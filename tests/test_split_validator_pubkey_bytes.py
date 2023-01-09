from eth_typing import HexStr

from web3_utils.is_null_address import is_null_address
from web3_utils.split_validator_pubkey_bytes import split_validator_pubkey_bytes


def test_split_validator_pubkey_bytes():
    VALIDATOR_PUB_KEY_1 = "1" * 96
    VALIDATOR_PUB_KEY_2 = "2" * 96
    VALIDATOR_PUB_KEY_3 = "3" * 96

    pubkey_bytes = "0x" + VALIDATOR_PUB_KEY_1 + VALIDATOR_PUB_KEY_2 + VALIDATOR_PUB_KEY_3

    pubkeys = split_validator_pubkey_bytes(HexStr(pubkey_bytes))
    assert pubkeys[0] == "0x" + VALIDATOR_PUB_KEY_1
    assert pubkeys[1] == "0x" + VALIDATOR_PUB_KEY_2
    assert pubkeys[2] == "0x" + VALIDATOR_PUB_KEY_3
