import os
import shutil
import tempfile
import pytest
from web3_utils.load_public_keys_from_files import load_public_keys_from_files

file_content = [
    "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    "0x111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",
    "0x222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222222",
    "0x333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333",
    "0x444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444444",
]


@pytest.fixture
def temp_dir_with_public_keys():
    temp_dir = tempfile.mkdtemp()
    files = ["bulk1-lighthouse0-pubkeys.txt", "nft1-teku0-pubkeys.txt", "nft1-teku1-pubkeys.txt"]

    for file_name in files:
        key_path = os.path.join(temp_dir, file_name)

        with open(key_path, "w") as f:
            for line in file_content:
                f.write(f"{line}\n")

    yield temp_dir

    shutil.rmtree(temp_dir)


def test_load_public_keys_from_files(temp_dir_with_public_keys):
    bulk = load_public_keys_from_files("bulk", temp_dir_with_public_keys)

    result = file_content.copy()
    assert len(bulk) == 5
    assert bulk == result

    nft = load_public_keys_from_files("nft", temp_dir_with_public_keys)

    result_b = file_content.copy()
    result_b.extend(file_content)
    assert len(nft) == 10
    assert nft == result_b
