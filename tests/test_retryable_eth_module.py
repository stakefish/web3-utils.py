import asyncio
import functools
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from requests import ConnectionError, HTTPError
from tenacity import wait_none
from web3 import AsyncHTTPProvider, AsyncWeb3, HTTPProvider
from web3.eth import AsyncEth, Eth
from web3.exceptions import (
    BlockNotFound,
    RequestTimedOut,
    TransactionNotFound,
    Web3RPCError,
)
from web3.main import Web3, get_default_modules

from web3_utils.retryable_eth_module import (
    RETRYABLE_RPC_METHODS,
    get_retryable_eth_module,
)


class StopOnShutdownFake:
    def __call__(self, retry_state: "RetryCallState") -> bool:
        return retry_state.attempt_number > 1


def retryable_web3():
    web3_modules = get_default_modules()
    web3_modules["eth"] = get_retryable_eth_module(Eth, logger=logging.getLogger(), retry_stop=StopOnShutdownFake)
    web3 = Web3(HTTPProvider("http://127.0.0.1:8545"), modules=web3_modules)
    return web3


def retryable_async_web3():
    return AsyncWeb3(
        AsyncHTTPProvider("http://127.0.0.1:8545"),
        modules={
            "eth": get_retryable_eth_module(
                AsyncEth,
                logger=logging.getLogger(),
                retry_stop=StopOnShutdownFake,
            )
        },
    )


def trigger_fake_error(error_to_raise, stop_after_attempt=1):
    def mocked_caller(method):
        state = {"counter": 0}

        def fun(*args, state, **kwargs):
            method.process_params(method._module, *args, **kwargs)

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
        return_value=trigger_fake_error(error_to_raise=BlockNotFound("block not found")),
    )

    web3 = retryable_web3()
    web3.eth.get_block(123)
    mocked_fn.assert_called()


def test_transaction_not_found_retry(mocker):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=trigger_fake_error(error_to_raise=TransactionNotFound("tx not found")),
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
    make_request = mocker.patch.object(
        HTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": "some other RPC error",
            },
        },
    )

    web3 = retryable_web3()

    with pytest.raises(Web3RPCError):
        web3.eth.get_block(123)

    assert make_request.call_count == 1


def test_stop_retry_on_shutdown(mocker: MockerFixture):
    mocked_fn: MagicMock = mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        # providing higher number of attempts on purpose
        return_value=trigger_fake_error(error_to_raise=BlockNotFound("block not found"), stop_after_attempt=5),
    )

    web3 = retryable_web3()

    with pytest.raises(BlockNotFound):
        web3.eth.get_block(123)

    mocked_fn.assert_called()


@pytest.mark.parametrize("timeout_type", ["rpc_response", "request_timed_out"])
@pytest.mark.parametrize(
    "rpc_method, expected",
    [
        # Node and fee queries
        ("eth_accounts", True),
        ("eth_blobBaseFee", True),
        ("eth_blockNumber", True),
        ("eth_chainId", True),
        ("eth_feeHistory", True),
        ("eth_gasPrice", True),
        ("eth_maxPriorityFeePerGas", True),
        ("eth_syncing", True),
        # Block queries
        ("eth_getBlockByHash", True),
        ("eth_getBlockByNumber", True),
        ("eth_getBlockReceipts", True),
        ("eth_getBlockTransactionCountByHash", True),
        ("eth_getBlockTransactionCountByNumber", True),
        # Transaction queries
        ("eth_getTransactionByHash", True),
        ("eth_getTransactionByBlockHashAndIndex", True),
        ("eth_getTransactionByBlockNumberAndIndex", True),
        ("eth_getRawTransactionByHash", True),
        ("eth_getRawTransactionByBlockHashAndIndex", True),
        ("eth_getRawTransactionByBlockNumberAndIndex", True),
        ("eth_getTransactionReceipt", True),
        # Account state queries
        ("eth_getBalance", True),
        ("eth_getCode", True),
        ("eth_getProof", True),
        ("eth_getStorageAt", True),
        ("eth_getTransactionCount", True),
        # Log queries
        ("eth_getLogs", True),
        ("eth_getFilterLogs", True),
        # Simulation and estimation
        ("eth_call", True),
        ("eth_createAccessList", True),
        ("eth_estimateGas", True),
        ("eth_simulateV1", True),
        # Transaction submission
        ("eth_sendTransaction", False),
        ("eth_sendRawTransaction", False),
        # Filter management
        ("eth_newFilter", False),
        ("eth_newBlockFilter", False),
        ("eth_newPendingTransactionFilter", False),
        ("eth_getFilterChanges", False),
        ("eth_uninstallFilter", False),
        # Subscription management
        ("eth_subscribe", False),
        ("eth_unsubscribe", False),
        # Signing
        ("eth_sign", False),
        ("eth_signTransaction", False),
        ("eth_signTypedData", False),
        # Unknown method
        ("eth_unknownMethod", False),
    ],
)
def test_rpc_retry_policy(mocker, rpc_method, expected, timeout_type):
    mocker.patch(
        "web3_utils.retryable_eth_module.wait_fixed",
        return_value=wait_none(),
    )

    if timeout_type == "request_timed_out":
        error = RequestTimedOut("request timed out")
    else:
        error = Web3RPCError(
            "request failed or timed out",
            rpc_response={
                "jsonrpc": "2.0",
                "id": 0,
                "error": {
                    "code": -32603,
                    "message": "request failed or timed out",
                },
            },
        )

    caller = mocker.Mock(side_effect=error)

    mocker.patch(
        "web3.module.retrieve_blocking_method_call_fn",
        return_value=lambda method: caller,
    )

    web3 = retryable_web3()
    method = SimpleNamespace(json_rpc_method=rpc_method)
    retryable_caller = web3.eth.retrieve_caller_fn(method)

    with pytest.raises(type(error)):
        retryable_caller()

    assert caller.call_count == (2 if expected else 1)


@pytest.mark.parametrize("block_identifier", [123, "0x" + "11" * 32])
def test_rpc_timeout_error_retry(mocker, block_identifier):
    make_request = mocker.patch.object(
        HTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {"code": -32603, "message": "request failed or timed out"},
        },
    )
    web3 = retryable_web3()
    with pytest.raises(Web3RPCError):
        web3.eth.get_block(block_identifier)
    assert make_request.call_count == 2


@pytest.mark.asyncio
async def test_async_rpc_timeout_error_retry(mocker):
    make_request = mocker.patch.object(
        AsyncHTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": "request failed or timed out",
            },
        },
    )

    web3 = retryable_async_web3()

    with pytest.raises(Web3RPCError):
        await web3.eth.get_block(123)

    assert make_request.call_count == 2


def test_send_raw_transaction_connection_error_does_not_retry(mocker):
    make_request = mocker.patch.object(
        HTTPProvider,
        "make_request",
        side_effect=ConnectionError("connection lost"),
    )

    web3 = retryable_web3()

    with pytest.raises(ConnectionError):
        web3.eth.send_raw_transaction(b"\x01")

    assert make_request.call_count == 1


def test_send_raw_transaction_timeout_does_not_retry(mocker):
    make_request = mocker.patch.object(
        HTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": "request failed or timed out",
            },
        },
    )

    web3 = retryable_web3()

    with pytest.raises(Web3RPCError):
        web3.eth.send_raw_transaction(b"\0x1")

    assert make_request.call_count == 1


def test_get_filter_changes_timeout_does_not_retry(mocker):
    make_request = mocker.patch.object(
        HTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": "request failed or timed out",
            },
        },
    )

    web3 = retryable_web3()
    with pytest.raises(Web3RPCError):
        web3.eth.get_filter_changes("0x1")

    assert make_request.call_count == 1


@pytest.mark.parametrize("block_identifier", [123, "0x" + "11" * 32])
def test_timeout_message_with_other_rpc_code_does_not_retry(mocker, block_identifier):
    make_request = mocker.patch.object(
        HTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {"code": -32000, "message": "request failed or timed out"},
        },
    )
    web3 = retryable_web3()
    with pytest.raises(Web3RPCError):
        web3.eth.get_block(block_identifier)
    assert make_request.call_count == 1


@pytest.mark.asyncio
async def test_async_send_raw_transaction_timeout_does_not_retry(mocker):
    make_request = mocker.patch.object(
        AsyncHTTPProvider,
        "make_request",
        return_value={
            "jsonrpc": "2.0",
            "id": 0,
            "error": {
                "code": -32603,
                "message": "request failed or timed out",
            },
        },
    )

    web3 = retryable_async_web3()

    with pytest.raises(Web3RPCError):
        await web3.eth.send_raw_transaction(b"\x01")

    assert make_request.await_count == 1
