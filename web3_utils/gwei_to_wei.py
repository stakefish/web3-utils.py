from decimal import Decimal


def gwei_to_wei(gwei: str) -> Decimal:
    return Decimal(gwei) * Decimal(10**9)
