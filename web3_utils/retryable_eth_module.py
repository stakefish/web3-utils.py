from __future__ import annotations
import asyncio
from http import HTTPStatus
import logging
import time
from typing import Type

import typing
from aiohttp import ClientConnectorError
from requests import HTTPError, ConnectionError
from tenacity import retry, retry_if_exception_type, wait_fixed, RetryCallState, retry_any, retry_if_exception, stop_never
from tenacity._utils import get_callback_name
from web3.eth import Eth, AsyncEth
from web3.exceptions import TransactionNotFound, BlockNotFound


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
    """Check if a ValueError is due to an rpc request timeout."""
    return isinstance(e, ValueError) and "request failed or timed out" in str(e)


def get_retryable_eth_module(base: Type[Eth] | Type[AsyncEth], logger: logging.Logger, retry_stop: typing.Callable or None = None):
    class RetryableModule(base):
        def __getattribute__(self, name):
            """
            "retrieve_caller_fn" returns a function which raises errors based on RPC results.
            We can also catch HTTPErrors and ConnectionErrors here
            """
            if name == "retrieve_caller_fn":
                return lambda *args, **kargs: retry(
                    retry=retry_any(
                        retry_if_exception_type(
                            (BlockNotFound, TransactionNotFound, ConnectionError, ClientConnectorError, asyncio.TimeoutError)
                        ),
                        retry_if_exception(is_retryable_http_error),
                        retry_if_exception(is_timeout_value_error),
                    ),
                    wait=wait_fixed(5),
                    reraise=True,
                    before=before,
                    before_sleep=before_sleep_log(logger=logger, log_level=logging.WARNING),
                    stop=retry_stop() if retry_stop else stop_never,
                )(object.__getattribute__(self, name)(*args, *kargs))
            else:
                return object.__getattribute__(self, name)

    return RetryableModule
