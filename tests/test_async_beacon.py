import contextvars
import logging

import pytest
from pytest_mock import MockerFixture
from requests import ConnectionError, HTTPError, Response

from web3_utils.async_beacon import AsyncBeacon

VALIDATOR_PUB_KEY_1 = "1" * 96



def trigger_fake_error(error_to_raise, stop_after_attempt=1):
    state = {"counter": 0}

    def fun(*dargs):
        if state["counter"] < stop_after_attempt:
            state["counter"] += 1
            raise error_to_raise

        return state["counter"], error_to_raise

    return fun


@pytest.mark.asyncio()
async def test_get_validator_not_found(mocker: MockerFixture):
    class Resp:
        status_code = 404

    mocked_fn = mocker.patch(
        "web3.beacon.Beacon.get_validator", side_effect=trigger_fake_error(error_to_raise=HTTPError(response=Resp()))
    )

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)

    response = await async_beacon.get_validator("0x" + VALIDATOR_PUB_KEY_1)
    assert response is None
    mocked_fn.assert_called_once_with("0x" + VALIDATOR_PUB_KEY_1, "head")


@pytest.mark.asyncio()
async def test_run_as_async_retries(mocker: MockerFixture):
    class Resp:
        def __init__(self, code: int):
            self.status_code = code

    for error_to_raise in [
        HTTPError(response=Resp(502)),
        HTTPError(response=Resp(429)),
        HTTPError(response=Resp(503)),
        HTTPError(response=Resp(500)),
        ConnectionError("Oops"),
    ]:
        mocker.patch(
            "web3.beacon.Beacon.get_validator", side_effect=trigger_fake_error(error_to_raise=error_to_raise, stop_after_attempt=2)
        )
        async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)
        retries, error = await async_beacon.get_validator("0x" + VALIDATOR_PUB_KEY_1)
        assert retries == 2
        if isinstance(error, HTTPError):
            assert error.response.status_code == error_to_raise.response.status_code


@pytest.mark.asyncio()
async def test_retry_stop_fn(mocker: MockerFixture):
    class Resp:
        def __init__(self, code: int):
            self.status_code = code

    class StopOnShutdownFake:
        def __call__(self, retry_state: "RetryCallState") -> bool:
            return retry_state.attempt_number > 1

    error_to_raise = HTTPError(response=Resp(502))
    mocker.patch(
        "web3.beacon.Beacon.get_validator", side_effect=trigger_fake_error(error_to_raise=error_to_raise, stop_after_attempt=99)
    )
    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=StopOnShutdownFake)

    with pytest.raises(Exception, match="HTTPError"):
        await async_beacon.get_validator("0x" + VALIDATOR_PUB_KEY_1)


@pytest.mark.asyncio()
async def test_cache_genesis_time(mocker: MockerFixture):
    mocked_fn = mocker.patch("web3.beacon.Beacon.get_genesis", return_value={"data": {"genesis_time": "1606824000"}})
    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)

    response = await async_beacon.get_genesis()
    response = await async_beacon.get_genesis()
    response = await async_beacon.get_genesis()
    response = await async_beacon.get_genesis()
    response = await async_beacon.get_genesis()
    assert response == 1606824000

    mocked_fn.assert_called_once()


@pytest.mark.asyncio()
async def test_get_validator_balances(mocker: MockerFixture):
    # Mock the get_validator_balances method from web3.beacon.Beacon
    response_json = {"data": [{"index": "0", "balance": "32000000000"}, {"index": "1", "balance": "32000000000"}]}
    mocked_response = Response()
    mocked_response.json = lambda: response_json
    mocked_response.status_code = 200

    mocked_fn = mocker.patch(
        "web3._utils.http_session_manager.HTTPSessionManager.get_response_from_get_request", return_value=mocked_response
    )

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)

    # Test with default parameters
    response = await async_beacon.get_validator_balances()
    assert response == response_json
    mocked_fn.assert_called_with(
        "http://127.0.0.1:8545/eth/v1/beacon/states/head/validator_balances", timeout=10.0, params={"id": None}
    )

    # Test with custom state_id and indexes
    indexes = ["0", "1"]
    state_id = "finalized"
    response = await async_beacon.get_validator_balances(state_id=state_id, indexes=indexes)
    print("RESP", response)
    assert response == response_json
    mocked_fn.assert_called_with(
        f"http://127.0.0.1:8545/eth/v1/beacon/states/{state_id}/validator_balances", timeout=10.0, params={"id": ["0", "1"]}
    )


@pytest.mark.asyncio()
async def test_get_pending_consolidations(mocker: MockerFixture):
    response_json = {"data": ["consolidation1", "consolidation2"]}
    mocked_response = mocker.patch("web3_utils.async_beacon.AsyncBeacon._get_pending_consolidations", return_value=response_json)
    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)
    response = await async_beacon.get_pending_consolidations()
    assert response == response_json
    mocked_response.assert_called_once_with("head")


@pytest.mark.asyncio()
async def test_get_pending_deposits(mocker: MockerFixture):
    response_json = {"data": ["deposit1", "deposit2"]}
    mocked_response = mocker.patch("web3_utils.async_beacon.AsyncBeacon._get_pending_deposits", return_value=response_json)
    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)
    response = await async_beacon.get_pending_deposits()
    assert response == response_json
    mocked_response.assert_called_once_with("head")


@pytest.mark.asyncio()
async def test_get_pending_partial_withdrawals(mocker: MockerFixture):
    response_json = {"data": ["withdrawal1", "withdrawal2"]}
    mocked_response = mocker.patch(
        "web3_utils.async_beacon.AsyncBeacon._get_pending_partial_withdrawals", return_value=response_json
    )
    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)
    response = await async_beacon.get_pending_partial_withdrawals()
    assert response == response_json
    mocked_response.assert_called_once_with("head")


test_context_var = contextvars.ContextVar("test_context_var", default=None)


@pytest.mark.asyncio()
async def test_run_as_async_propagates_context_vars():
    """Context variables set in the async caller should be visible inside the executor thread."""
    test_context_var.set("hello_from_async")

    def sync_fn_reads_context():
        return test_context_var.get()

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)
    result = await async_beacon._run_as_async(sync_fn_reads_context)

    assert result == "hello_from_async"


@pytest.mark.asyncio()
async def test_run_as_async_context_is_a_copy():
    """Mutations to context variables inside the executor should not leak back to the caller."""
    test_context_var.set("original")

    def sync_fn_mutates_context():
        test_context_var.set("mutated_in_thread")
        return test_context_var.get()

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)
    result = await async_beacon._run_as_async(sync_fn_mutates_context)

    # The executor thread saw the mutated value
    assert result == "mutated_in_thread"
    # But the caller's context is unchanged because copy_context() was used
    assert test_context_var.get() == "original"


@pytest.mark.asyncio()
async def test_run_as_async_passes_func_and_args_through_ctx_run():
    """func and *args are correctly forwarded through ctx.run(func, *args)."""

    def sync_fn_with_args(a, b, c):
        return (a, b, c)

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)

    result = await async_beacon._run_as_async(sync_fn_with_args, "x", 42, [1, 2])
    assert result == ("x", 42, [1, 2])


@pytest.mark.asyncio()
async def test_run_as_async_passes_single_arg():
    """A single positional arg is forwarded correctly (not accidentally unpacked)."""

    def sync_fn_single_arg(value):
        return value

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)

    result = await async_beacon._run_as_async(sync_fn_single_arg, "only_one")
    assert result == "only_one"


@pytest.mark.asyncio()
async def test_run_as_async_passes_no_args():
    """Calling with zero extra args works (func receives nothing beyond what ctx.run provides)."""

    def sync_fn_no_args():
        return "no_args_ok"

    async_beacon = AsyncBeacon("http://127.0.0.1:8545", logger=logging.getLogger(), retry_stop=None)

    result = await async_beacon._run_as_async(sync_fn_no_args)
    assert result == "no_args_ok"
