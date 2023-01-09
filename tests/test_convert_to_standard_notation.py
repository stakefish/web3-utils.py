from decimal import Decimal

from web3_utils.convert_to_standard_notation import convert_to_standard_notation


def test_convert_to_standard_notation():
    balance = Decimal(12.3456789)
    expected = "12"

    assert convert_to_standard_notation(balance) == expected
