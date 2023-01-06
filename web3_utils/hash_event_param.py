from web3 import Web3


def hash_event_param(param: str):
    return str(Web3.toHex(Web3.solidityKeccak(["bytes"], [param])))
