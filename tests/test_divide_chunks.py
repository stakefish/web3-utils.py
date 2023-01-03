import pytest

from web3_utils.divide_chunks import divide_chunks


def test_divide_chunks():
    input = list(range(0, 50))
    output = list(divide_chunks(input, 50))
    assert len(output) == 1
    assert output[0] == input

    input = list(range(0, 52))
    output = list(divide_chunks(input, 50))
    assert len(output) == 2
    assert output[0] == list(range(0, 50))
    assert output[1] == [50, 51]

    input = list(range(0, 102))
    output = list(divide_chunks(input, 50))
    assert len(output) == 3
    assert output[0] == list(range(0, 50))
    assert output[1] == list(range(50, 100))
    assert output[2] == [100, 101]
