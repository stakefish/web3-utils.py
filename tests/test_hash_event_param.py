from web3_utils.hash_event_param import hash_event_param


def test_hash_event_param():
    expected = "0x79fad56e6cf52d0c8c2c033d568fc36856ba2b556774960968d79274b0e6b944"

    assert hash_event_param("0x123456789") == expected
