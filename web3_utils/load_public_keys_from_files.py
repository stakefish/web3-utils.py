from os import path, listdir, getcwd
from typing import TypedDict


def read_public_keys_from_file(file_path: str):
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
        return lines


def load_public_keys_from_files(type: str, dir_path: str = path.join(getcwd(), "tmp", "public_keys")):
    files = listdir(dir_path)
    result = []

    for file in files:
        if file.startswith(type):
            file_path = path.join(dir_path, file)
            public_keys = read_public_keys_from_file(file_path)
            result.extend(public_keys)

    return result


class PublicKeyFile(TypedDict):
    public_keys: list[str]
    file_name: str
    type: str


# Seperate function introduced that returns the pubkeys on a per file basis as to not break existing code that uses the previous function
def load_public_key_files(type: str, dir_path: str = path.join(getcwd(), "tmp", "public_keys")) -> list[PublicKeyFile]:
    files = listdir(dir_path)
    public_key_files: list[PublicKeyFile] = []

    for file in files:
        if file.startswith(type):
            file_name = file.split(".")[0]  # strip file extension
            file_path = path.join(dir_path, file)
            public_keys = read_public_keys_from_file(file_path)
            public_key_files.append({"public_keys": public_keys, "file_name": file_name, "type": type})

    return public_key_files
