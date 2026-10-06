from __future__ import annotations

import asyncio
import logging
import time
import typing
from http import HTTPStatus
from typing import Type

from aiohttp import ClientConnectorError
from requests import ConnectionError, HTTPError
from tenacity import (
    RetryCallState,
    retry,
    retry_all,
    retry_any,
    retry_if_exception,
    retry_if_exception_type,
    stop_never,
    wait_fixed,
)
from tenacity._utils import get_callback_name
from web3.eth import AsyncEth, Eth
from web3.exceptions import (
    BlockNotFound,
    RequestTimedOut,
    TransactionNotFound,
    Web3RPCError,
)

RETRYABLE_RPC_METHODS = frozenset(
    {
        # Node and fee queries
        "eth_accounts",
        "eth_blobBaseFee",
        "eth_blockNumber",
        "eth_chainId",
        "eth_feeHistory",
        "eth_gasPrice",
        "eth_maxPriorityFeePerGas",
        "eth_syncing",
        # Block queries
        "eth_getBlockByHash",
        "eth_getBlockByNumber",
        "eth_getBlockReceipts",
        "eth_getBlockTransactionCountByHash",
        "eth_getBlockTransactionCountByNumber",
        # Transaction queries
        "eth_getTransactionByHash",
        "eth_getTransactionByBlockHashAndIndex",
        "eth_getTransactionByBlockNumberAndIndex",
        "eth_getRawTransactionByHash",
        "eth_getRawTransactionByBlockHashAndIndex",
        "eth_getRawTransactionByBlockNumberAndIndex",
        "eth_getTransactionReceipt",
        # Account state queries
        "eth_getBalance",
        "eth_getCode",
        "eth_getProof",
        "eth_getStorageAt",
        "eth_getTransactionCount",
        # Log queries
        "eth_getLogs",
        "eth_getFilterLogs",
        # Simulation and estimation
        "eth_call",
        "eth_createAccessList",
        "eth_estimateGas",
        "eth_simulateV1",
    }
)


def before_sleep_log(
    logger: "logging.Logger",
    log_level: int,
    exc_info: bool = False,
) -> typing.Callable[["RetryCallState"], None]:
    """Before call strategy that logs to some logger the attempt."""

    def log_it(retry_state: "RetryCallState") -> None:
        if retry_state.outcome.failed:
            ex = retry_state.outcome.exception()
            verb, value = "raised", f"{ex.__class__.__name__}: {ex}"

            if exc_info:
                local_exc_info = retry_state.outcome.exception()
            else:
                local_exc_info = False
        else:
            verb, value = "returned", retry_state.outcome.result()
            local_exc_info = False  # exc_info does not apply when no exception

        logger.log(
            log_level,
            f"Failed after {'%0.3f' % retry_state.seconds_since_start}(s) "
            f"Retrying {get_callback_name(retry_state.fn)} "
            f"Args {retry_state.args} "
            f"Kwargs {retry_state.kwargs} "
            f"in {retry_state.next_action.sleep} seconds as it {verb} {value}.",
            exc_info=local_exc_info,
        )

    return log_it


def before(retry_state: "RetryCallState"):
    retry_state.start_time = time.monotonic()


def is_retryable_http_error(e) -> bool:
    """Check for retryable HTTP status codes"""
    return isinstance(e, HTTPError) and e.response.status_code in [
        HTTPStatus.TOO_MANY_REQUESTS,
        HTTPStatus.BAD_GATEWAY,
        HTTPStatus.GATEWAY_TIMEOUT,
    ]


def is_timeout_value_error(e) -> bool:
    """Check if a Web3RPCError is due to an rpc request timeout."""
    if isinstance(e, RequestTimedOut):
        return True
    if not isinstance(e, Web3RPCError):
        return False
    response = e.rpc_response or {}
    error = response.get("error", {})
    return error.get("code") == -32603 and "request failed or timed out" in error.get("message", "")


def get_retryable_eth_module(base: Type[Eth] | Type[AsyncEth], logger: logging.Logger, retry_stop: typing.Callable or None = None):
    class RetryableModule(base):
        def __getattribute__(self, name):
            """
            "retrieve_caller_fn" returns a function which raises errors based on RPC results.
            We can also catch HTTPErrors and ConnectionErrors here
            """
            if name == "retrieve_caller_fn":
                original_factory = object.__getattribute__(self, name)

                def retrieve_retryable_caller(*args, **kwargs):
                    method = args[0]
                    caller = original_factory(*args, **kwargs)

                    return retry(
                        retry=retry_all(
                            retry_if_exception(lambda e: method.json_rpc_method in RETRYABLE_RPC_METHODS),
                            retry_any(
                                retry_if_exception_type(
                                    (
                                        BlockNotFound,
                                        TransactionNotFound,
                                        ConnectionError,
                                        ClientConnectorError,
                                        asyncio.TimeoutError,
                                    )
                                ),
                                retry_if_exception(is_retryable_http_error),
                                retry_if_exception(is_timeout_value_error),
                            ),
                        ),
                        wait=wait_fixed(5),
                        reraise=True,
                        before=before,
                        before_sleep=before_sleep_log(logger=logger, log_level=logging.WARNING),
                        stop=retry_stop() if retry_stop else stop_never,
                    )(caller)

                return retrieve_retryable_caller
            else:
                return object.__getattribute__(self, name)

    return RetryableModule
