from web3_utils.compute_time_at_slot import compute_time_at_slot


def test_compute_time_at_slot():
    genesis_time = 1000
    expected = 1120

    assert compute_time_at_slot(genesis_time, 10) == expected
