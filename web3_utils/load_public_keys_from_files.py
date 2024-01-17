from os import path, listdir, getcwd


def load_public_keys_from_files(type: str, dir_path: str = path.join(getcwd(), "tmp", "public_keys")):
    files = listdir(dir_path)
    result = []

    for file in files:
        if file.startswith(type):
            file_path = path.join(dir_path, file)

            with open(file_path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
                result.extend(lines)

    return result
