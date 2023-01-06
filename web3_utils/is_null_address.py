from eth_typing import HexStr, HexAddress
from web3.constants import ADDRESS_ZERO


def is_null_address(address: HexStr):
    return HexAddress(address) == HexAddress(HexStr(ADDRESS_ZERO)) or HexAddress(address) == HexAddress(HexStr("0x0"))
