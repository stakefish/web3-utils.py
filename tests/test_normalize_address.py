from web3_utils.normalize_address import normalize_address


def test_normalize_address():
    raw_address = "0xc00f6cf15ab248989838aa01d25177ec2510a81d"

    normalized_address = normalize_address(raw_address)
    assert normalized_address == "0xC00f6cf15Ab248989838AA01D25177ec2510A81D"
