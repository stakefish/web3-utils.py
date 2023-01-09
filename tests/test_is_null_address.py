from eth_typing import HexStr

from web3_utils.is_null_address import is_null_address


def test_is_null_address():
    assert is_null_address(HexStr("0x0")) is True
    assert is_null_address(HexStr("0x9308245A3Ca756b506fa1D3a1962b5a563F92470")) is False
