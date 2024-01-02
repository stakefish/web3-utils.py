import logging

import pytest
from pytest_mock import MockerFixture
from requests import HTTPError, ConnectionError

from web3_utils.async_beacon import AsyncBeacon

VALIDATOR_PUB_KEY_1 = "1" * 96


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


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
