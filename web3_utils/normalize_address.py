from eth_typing import ChecksumAddress, HexStr
from web3 import Web3
from web3.exceptions import InvalidAddress


def normalize_address(address: str) -> ChecksumAddress:
    if Web3.is_address(address) == False:
        raise InvalidAddress(address)

    return Web3.to_checksum_address(HexStr(address))
