from web3 import Web3


async def calculate_max_tx_fees(async_web3: Web3):
    latest_block = await async_web3.eth.get_block("latest")
    max_priority_fee_per_gas = await async_web3.eth.max_priority_fee
    max_fee_per_gas = max_priority_fee_per_gas + (2 * latest_block["baseFeePerGas"])

    return max_fee_per_gas, max_priority_fee_per_gas
