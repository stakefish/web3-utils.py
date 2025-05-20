import asyncio
import logging
from typing import Any, Dict, List, Callable

from eth_typing import URI
from requests import HTTPError, ConnectionError, Session
from tenacity import retry, retry_if_exception, wait_fixed, before_sleep_log, retry_any, retry_if_exception_type, stop_never
from web3.beacon import Beacon
from web3._utils.request import json_make_get_request, cache_and_return_session


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
        self.cache = {}

    async def get_syncing(self):
        return await self._run_as_async(super().get_syncing)

    async def get_finality_checkpoint(self, state_id: str = "head"):
        return await self._run_as_async(super().get_finality_checkpoint, state_id)

    async def get_genesis(self) -> int:
        if "genesis_time" not in self.cache:
            genesis = await self._run_as_async(super().get_genesis)
            self.cache["genesis_time"] = int(genesis["data"]["genesis_time"])

        return self.cache["genesis_time"]

    async def get_validator(self, pubkey: str, state_id: str = "head"):
        return await self._run_as_async(self._get_validator, pubkey, state_id)

    async def get_validators(self, state_id: str = "head", ids: List[str] = None, statuses: List[str] = None) -> Dict[str, Any]:
        return await self._run_as_async(self._get_validators, state_id, ids, statuses)

    async def get_validator_balances(self, state_id: str = "head", indexes: List[str] = None) -> Dict[str, Any]:
        return await self._run_as_async(self._get_validator_balances, state_id, indexes)

    async def get_pending_consolidations(self, state_id: str = "head"):
        return await self._run_as_async(self._get_pending_consolidations, state_id)

    async def get_pending_deposits(self, state_id: str = "head"):
        return await self._run_as_async(self._get_pending_deposits, state_id)

    async def get_pending_partial_withdrawals(self, state_id: str = "head"):
        return await self._run_as_async(self._get_pending_partial_withdrawals, state_id)

    def _get_validator(self, pubkey: str, state_id: str = "head"):
        try:
            return super().get_validator(pubkey, state_id)
        except HTTPError as e:
            if e.response.status_code == 404:
                self.logger.info(f"BEACON CHAIN: Validator {pubkey} was not found, probably is not active yet | State: {state_id}")
                return None
            else:
                raise e

    def _get_validators(self, state_id: str = "head", ids: List[str] = None, statuses: List[str] = None) -> Dict[str, Any]:
        endpoint = f"/eth/v1/beacon/states/{state_id}/validators"

        request_body = {}
        if ids is not None:
            request_body["ids"] = ids
        if statuses is not None:
            request_body["statuses"] = statuses

        return self._make_post_request(endpoint, request_body)

    def _get_validator_balances(self, state_id: str = "head", indexes: List[str] = None) -> Dict[str, Any]:
        endpoint = f"/eth/v1/beacon/states/{state_id}/validator_balances"
        params = {"id": indexes}

        return self._make_get_request_with_params(endpoint, params)

    def _get_pending_consolidations(self, state_id: str = "head"):
        endpoint = f"/eth/v1/beacon/states/{state_id}/pending_consolidations"
        return self._make_get_request_with_params(endpoint, params=None)

    def _get_pending_deposits(self, state_id: str = "head"):
        endpoint = f"/eth/v1/beacon/states/{state_id}/pending_deposits"
        return self._make_get_request_with_params(endpoint, params=None)

    def _get_pending_partial_withdrawals(self, state_id: str = "head"):
        endpoint = f"/eth/v1/beacon/states/{state_id}/pending_partial_withdrawals"
        return self._make_get_request_with_params(endpoint, params=None)

    def _make_get_request_with_params(self, endpoint: str, params: Any) -> Dict[str, Any]:
        uri = URI(self.base_url + endpoint)
        return json_make_get_request(uri, timeout=self.request_timeout, params=params)

    def _make_post_request(self, endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        uri = self.base_url + endpoint
        session = cache_and_return_session(uri)
        response = session.post(uri, json=json_data)
        response.raise_for_status()
        return response.json()

    @with_retry
    async def _run_as_async(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
