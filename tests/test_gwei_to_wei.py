from web3_utils.convert_to_standard_notation import convert_to_standard_notation
from web3_utils.gwei_to_wei import gwei_to_wei


def test_regression_test_for_incorrect_gwei_to_wei_conversion():
    gwei = "32000130042"
    wei = gwei_to_wei(gwei)

    assert convert_to_standard_notation(wei) == "32000130042000000000"
