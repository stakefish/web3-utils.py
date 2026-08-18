# CLAUDE.md — web3-utils.py

Context for AI agents working in this repository. Read this before changing anything.

## What this is

`stakefish-web3-utils`, a small internal library of Web3/beacon-chain helpers on PyPI. It has no
application logic of its own — every change here is a change to somebody else's runtime.

**Match the consuming service when choosing versions** — dependency, Python or Node. Its lockfile is the
reference, not this repo's pins; see the trap below for why.

## The trap that matters most

`install_requires` in `setup.cfg` is **unpinned** (`web3>=7`, `tenacity`, `python-gitlab`).
`requirements.txt` pins are therefore **CI-only**: they decide what the tests run against, not what
consumers install. The two drift silently, and CI happily tests a version nobody runs — this repo once
tested `gitlab.py` against python-gitlab 5.6.0 while production ran 8.3.0, three majors apart.

When touching dependencies, check what the consumer's lockfile actually resolves, not what this repo
pins.

## Conventions

- **Formatting** — `black` (line-length 132) and `isort` (`profile = "black"`), both enforced by
  `make lint` in CI. Run `make format` before pushing.
- **Python floor is 3.9** (`python_requires` in `setup.cfg`) even though CI runs 3.14. So no `int | str`
  in annotations — that is evaluated at definition time and raises on 3.9. Use `Union[int, str]`.
- **Comments** earn their place: one line, only for what the code cannot say. Prefer explaining *why* a
  non-obvious choice was made over restating the call being made.
- **Never commit or push.** Stage changes with `git add` and let the human commit. This repo signs
  commits with GPG, so an agent attempting a commit will hang on pinentry anyway.

## AsyncBeacon

`AsyncBeacon` extends web3's synchronous `Beacon` and overrides selected methods as async, always in
pairs — a public `async def get_X` delegating through `_run_as_async`, and a private `_get_X` that
builds the endpoint:

```python
async def get_attestations_rewards(self, epoch: Union[int, str], validator_indices: List[str]) -> Dict[str, Any]:
    return await self._run_as_async(self._get_attestations_rewards, epoch, validator_indices)

def _get_attestations_rewards(self, epoch: Union[int, str], validator_indices: List[str]) -> Dict[str, Any]:
    endpoint = f"/eth/v1/beacon/rewards/attestations/{epoch}"
    return self._make_post_request(endpoint, validator_indices)
```

Two failure modes worth knowing:

- **POST bodies are a bare JSON array of validator indices**, not an object. Wrapping the list does not
  error — the node reads an unrecognised body as *every validator* and returns the whole set. Tests
  assert the exact `post(url, json=[...])` call for this reason.
- **Overriding a sync method with an async one breaks synchronous callers** of that name. It is the
  established pattern, but grep the consumers before converting one that is already in use.

Endpoints that answer about *past* epochs (attestation rewards, liveness, proposer duties) degrade on a
non-archive node: they 404 rather than returning partial data. Callers must treat "no answer" as no
verdict, never as a negative result.

## Testing

```bash
make test                                # pytest tests/ -s
pytest tests/ -p no:pytest-brownie       # if another project's plugins are on your path
```

Tests are HTTP-mocked; nothing needs a running node, and `hardhat` in `package.json` is currently unused
by any test. `pytest-asyncio` is 1.x, which **removed the `event_loop` fixture** — an async test uses
`@pytest.mark.asyncio()` and takes no loop fixture.

## Releasing

Automated. Pushing a `v*` tag runs `.github/workflows/publish.yml` → verify, build, publish to PyPI via
Trusted Publishing (OIDC, no API token). The version bump belongs **in the pull request**, because `main`
requires review and nothing should be committed to it directly.

`scripts/check_version_bump.py` gates PRs: packaged changes need a bump above the base version,
`setup.cfg` and `.bumpversion.cfg` must agree, and the target tag must not already exist. Use
`bumpversion patch|minor|major` rather than editing versions by hand — editing one file by hand breaks
the tool that owns both.

## CI gotchas

- `make install` shells out to `uv`, which GitHub runners do not ship — workflows `pip install uv` first.
- `uv pip install` refuses to install outside a virtualenv. CI sets `UV_SYSTEM_PYTHON: 1` rather than
  putting `--system` in the Makefile, which would make a local `make install` bypass the developer's own
  virtualenv.
- Python and Node versions come from `.python-version` and `.nvmrc` via `python-version-file` /
  `node-version-file`, so local tooling and CI cannot disagree.
