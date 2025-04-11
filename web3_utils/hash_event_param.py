from web3 import Web3


def hash_event_param(param: str):
    return str(Web3.to_hex(Web3.solidity_keccak(["bytes"], [param])))
