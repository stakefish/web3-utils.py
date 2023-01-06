from eth_typing import HexStr

PUBKEY_LENGTH = 96


def split_validator_pubkey_bytes(pubkeys: HexStr):
    """
    Splits batchDeposit pubkey bytes into individual pubkeys
    """
    pubkeys_raw = pubkeys.replace("0x", "")
    return ["0x" + pubkeys_raw[idx : idx + PUBKEY_LENGTH] for idx in range(0, len(pubkeys_raw), PUBKEY_LENGTH)]
