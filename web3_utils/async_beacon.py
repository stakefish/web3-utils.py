import asyncio
import logging
from typing import Any, Dict, List, Callable

from requests import HTTPError, ConnectionError
from tenacity import retry, retry_if_exception, wait_fixed, before_sleep_log, retry_any, retry_if_exception_type, stop_never
from web3.beacon import Beacon


def with_retry(f):
    async def wrapper(*args):
        retry_stop = args[0].retry_stop

        @retry(
            retry=retry_any(
                retry_if_exception_type(ConnectionError),
                retry_if_exception(lambda e: isinstance(e, HTTPError) and e.response.status_code in [429, 502, 503, 500]),
            ),
            stop=retry_stop() if retry_stop else stop_never,
            wait=wait_fixed(5),
            before_sleep=before_sleep_log(logger=args[0].logger, log_level=logging.WARNING),
        )
        async def execute():
            return await f(*args)

        return await execute()

    return wrapper


class AsyncBeacon(Beacon):
    def __init__(self, base_url: str, logger: logging.Logger, retry_stop: Callable or None = None):
        super().__init__(base_url)
        self.retry_stop = retry_stop
        self.logger = logger

    async def get_finality_checkpoint(self, state_id: str = "head"):
        return await self._run_as_async(super().get_finality_checkpoint, state_id)

    async def get_genesis(self) -> int:
        genesis = await self._run_as_async(super().get_genesis)
        genesis_time = int(genesis["data"]["genesis_time"])
        return genesis_time

    async def get_validator(self, pubkey: str, state_id: str = "head"):
        return await self._run_as_async(self._get_validator, pubkey, state_id)

    async def get_validators(self, state_id: str = "head", indexes: List[str] = None) -> Dict[str, Any]:
        return await self._run_as_async(self._get_validators, state_id, indexes)

    async def get_validator_balances(self, state_id: str = "head", indexes: List[str] = None) -> Dict[str, Any]:
        return await self._run_as_async(self._get_validator_balances, state_id, indexes)

    def _get_validator(self, pubkey: str, state_id: str = "head"):
        try:
            return super().get_validator(pubkey, state_id)
        except HTTPError as e:
            if e.response.status_code == 404:
                self.logger.info(f"BEACON CHAIN: Validator {pubkey} was not found, probably is not active yet | State: {state_id}")
                return None
            else:
                raise e

    def _get_validators(self, state_id: str = "head", indexes: List[str] = None) -> Dict[str, Any]:
        if indexes is None or len(indexes) > 50:
            raise Exception("Too many validators requested")

        endpoint = f"/eth/v1/beacon/states/{state_id}/validators"
        params = {"id": indexes}

        return self._make_get_request_with_params(endpoint, params)

    def _get_validator_balances(self, state_id: str = "head", indexes: List[str] = None) -> Dict[str, Any]:
        if indexes is None or len(indexes) > 250:
            raise Exception("Too many validators requested")

        endpoint = f"/eth/v1/beacon/states/{state_id}/validator_balances"
        params = {"id": indexes}

        return self._make_get_request_with_params(endpoint, params)

    def _make_get_request_with_params(self, endpoint: str, params: Any) -> Dict[str, Any]:
        url = self.base_url + endpoint
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @with_retry
    async def _run_as_async(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
