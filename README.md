# web3-utils

Internal Web3 utilities for Python, shared across stakefish services. The pinned Python and Node
versions here track the services that consume it, so a change cannot land on a toolchain they do not
run.

Published to PyPI as [`stakefish-web3-utils`](https://pypi.org/project/stakefish-web3-utils/).

## What's in it

| Module | Purpose |
| --- | --- |
| `async_beacon` | `AsyncBeacon` — beacon-chain API client; async overrides of web3's sync `Beacon` |
| `retryable_eth_module` | Wraps an eth module so transient RPC failures retry instead of surfacing |
| `gitlab` | Downloads validator pubkey files from a GitLab project |
| `calculate_max_fees`, `gwei_to_wei`, `convert_to_standard_notation` | Fee and unit conversion |
| `compute_time_at_slot`, `current_utc_timestamp` | Beacon slot/epoch time arithmetic |
| `normalize_address`, `is_null_address`, `hash_event_param` | Address and event helpers |
| `split_validator_pubkey_bytes`, `load_public_keys_from_files`, `divide_chunks` | Pubkey and batching helpers |

## Development

Requires the pinned Python (`.python-version`) and Node (`.nvmrc`) — `pyenv` and `nvm` both read them.

```bash
python -m venv .venv && source .venv/bin/activate
make install
```

`make install` uses `uv`, which must be on your PATH (`pip install uv`). It installs into whatever
environment is active, so activate your virtualenv first — otherwise uv refuses to install at all
rather than silently targeting your system Python.

```bash
make lint     # black --check and isort --check
make format   # black
make test     # pytest
```

If another project's pytest plugins are on your path — a brownie plugin, for instance — pytest may try
to spawn `ganache-cli` and die before collecting. Run `pytest tests/ -p no:pytest-brownie`.

### Adding a beacon endpoint

`AsyncBeacon` extends web3's synchronous `Beacon` and overrides selected methods as async, in pairs:

```python
async def get_spec(self) -> Dict[str, Any]:
    return await self._run_as_async(self._get_spec)

def _get_spec(self) -> Dict[str, Any]:
    endpoint = "/eth/v1/config/spec"
    return self._make_get_request_with_params(endpoint, params=None)
```

Two things to be careful about:

- **POST endpoints take a bare JSON array**, not an object — `_make_post_request(endpoint, validator_indices)`.
  Wrapping the list in `{"indices": [...]}` does not error; the node interprets an unrecognised body as
  *every validator* and returns the whole set.
- **Overriding a sync method with an async one breaks synchronous callers** of that name. That is the
  established pattern here, but check the consumers before converting one.

## Releasing

Publishing is automated. Pushing a `v*` tag runs `.github/workflows/publish.yml`, which verifies, builds
and publishes to PyPI via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — there is no
API token, and nothing to rotate.

1. Bump the version **in the pull request**, not on `main`:

   ```bash
   bumpversion patch    # or minor / major
   ```

   This rewrites `setup.cfg` and `.bumpversion.cfg` together and creates the tag locally. Both files
   must agree, or `bumpversion` cannot find the string it rewrites — `scripts/check_version_bump.py`
   fails the PR when they drift, and when packaged code changes without a bump.

   A PR that touches only CI, tests or docs needs no bump. Use the `skip-version-check` label for the
   rare case a rule cannot judge, such as batching several merges into one release.

2. Merge the PR through review, as normal.
3. Push the tag: `git push origin v<version>`. The publish workflow takes it from there.

The `build` job refuses to publish when the tag disagrees with `setup.cfg`, so a mistagged release fails
before it reaches PyPI — where a version can never be reused.

### Which version part to bump

`{major}.{minor}.{patch}` for stable, `{major}.{minor}.{patch}{stage}.{devnum}` for unstable, where
stage is `b` or `rc`. From a beta, `bumpversion stage` moves to `rc`; from an `rc`, to stable.

### Verifying a build locally

```bash
uv pip install --upgrade build
make package    # builds the wheel and smoke-tests it in a temporary virtualenv
```
