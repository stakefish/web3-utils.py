import asyncio
import functools
import logging
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from requests import HTTPError, ConnectionError
from web3 import HTTPProvider
from web3.eth import Eth
from web3.exceptions import BlockNotFound, TransactionNotFound
from web3.main import get_default_modules, Web3
from web3.types import RPCError

from web3_utils.retryable_eth_module import get_retryable_eth_module


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


class StopOnShutdownFake:
    def __call__(self, retry_state: "RetryCallState") -> bool:
        return retry_state.attempt_number > 1


def retryable_web3():
    web3_modules = get_default_modules()
    web3_modules["eth"] = get_retryable_eth_module(Eth, logger=logging.getLogger(), retry_stop=StopOnShutdownFake)
    web3 = Web3(HTTPProvider("http://127.0.0.1:8545"), modules=web3_modules)
    return web3


def trigger_fake_error(error_to_raise, stop_after_attempt=1):
    def mocked_caller(*args):
        state = {"counter": 0}

        def fun(*args2, state):
            if state["counter"] < stop_after_attempt:
                state["counter"] += 1
                raise error_to_raise

        return functools.partial(fun, state=state)

    return mocked_caller


def test_http_429_retry(mocker):
    class Resp:
        status_code = 429

    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=HTTPError(response=Resp())),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_http_504_retry(mocker):
    class Resp:
        status_code = 504

    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=HTTPError(response=Resp())),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_block_not_found_retry(mocker):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=BlockNotFound()),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_transaction_not_found_retry(mocker):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=TransactionNotFound()),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_connection_error_retry(mocker):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=ConnectionError()),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_timeout_error_retry(mocker):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=asyncio.TimeoutError()),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_other_error_do_not_retry(mocker: MockerFixture):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=ConnectionError()),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_stop_retry_on_shutdown(mocker: MockerFixture, event_loop):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        # providing higher number of attempts on purpose
        return_value=trigger_fake_error(error_to_raise=BlockNotFound(), stop_after_attempt=5),
    )

    web3 = retryable_web3()

    with pytest.raises(BlockNotFound):
        web3.eth.get_block(123)

    mocked_fn.assert_called()


def test_rpc_timeout_error_retry(mocker):
    rpc_timeout_error = RPCError(code=-32603, message="request failed or timed out")
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=ValueError(rpc_timeout_error)),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()
