import base64
import re
import shutil
from os import path, makedirs, getcwd
from gitlab import Gitlab
from typing import Optional


class GitLab:
    def __init__(self, url: str, token: str, tmp_dir: str = path.join(getcwd(), "tmp", "public_keys")):
        self.client = Gitlab(private_token=token, url=url)
        self.tmp_dir = tmp_dir

    def download_files_from_project(
        self, project_id: int, dir_path: str, branch: str = "master", include_only_files: Optional[list[str]] = None
    ):
        # ensures that access token doesn't expire
        self.client.auth()

        project = self.client.projects.get(project_id)
        items = project.repository_tree(ref=branch, path=dir_path, get_all=True)
        if include_only_files:
            items = [item for item in items if any(re.match(pattern, item["name"]) for pattern in include_only_files)]

        self._prepare_temp_directory()

        downloaded_files = []
        for item in items:
            if item["type"] == "blob":
                file_path = path.join(self.tmp_dir, item["name"])
                with open(file_path, "w") as file:
                    blob = project.repository_blob(item["id"])
                    decoded_bytes = base64.b64decode(blob["content"])
                    decoded_string = decoded_bytes.decode("utf-8")
                    file.write(decoded_string)
                downloaded_files.append(file_path)

        return downloaded_files

    def _prepare_temp_directory(self):
        if path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

        makedirs(self.tmp_dir, exist_ok=True)
