import base64
import os
import pytest
from unittest.mock import Mock
from web3_utils.gitlab import GitLab


@pytest.fixture
def gitlab_instance(mocker):
    gitlab_mock = Mock()
    mocker.patch("web3_utils.gitlab.Gitlab", return_value=gitlab_mock)

    gitlab = GitLab(url="fake_url", token="fake_token")
    return gitlab, gitlab_mock


def test_download_files_from_project(gitlab_instance, mocker):
    gitlab, gitlab_mock = gitlab_instance

    repo_tree_mock = mocker.patch.object(
        gitlab_mock.projects.get(1),
        "repository_tree",
        return_value=[
            {"id": "file_id_1", "name": "file1.txt", "type": "blob"},
            {"id": "file_id_2", "name": "file2.txt", "type": "blob"},
        ],
    )

    repo_blob_mock = mocker.patch.object(
        gitlab_mock.projects.get(1),
        "repository_blob",
        side_effect=[
            {"content": base64.b64encode(b"file1 content").decode("utf-8")},
            {"content": base64.b64encode(b"file2 content").decode("utf-8")},
        ],
    )

    downloaded_files = gitlab.download_files_from_project(project_id=1, dir_path="test_dir", branch="main")

    expected_paths = [
        os.path.join(os.getcwd(), "tmp", "public_keys", "file1.txt"),
        os.path.join(os.getcwd(), "tmp", "public_keys", "file2.txt"),
    ]
    assert downloaded_files == expected_paths
    repo_tree_mock.assert_called_once_with(ref="main", path="test_dir", get_all=True)
    repo_blob_mock.assert_has_calls([mocker.call("file_id_1"), mocker.call("file_id_2")])


def test_download_files_from_project_with_include_only_files(gitlab_instance, mocker):
    gitlab, gitlab_mock = gitlab_instance

    repo_tree_mock = mocker.patch.object(
        gitlab_mock.projects.get(1),
        "repository_tree",
        return_value=[
            {"id": "file_id_1", "name": "hoodi-file.txt", "type": "blob"},
            {"id": "file_id_2", "name": "holesky-file.txt", "type": "blob"},
            {"id": "file_id_3", "name": "not-hoodi.txt", "type": "blob"},
        ],
    )

    repo_blob_mock = mocker.patch.object(
        gitlab_mock.projects.get(1),
        "repository_blob",
        side_effect=[
            {"content": base64.b64encode(b"file1 content").decode("utf-8")},
            {"content": base64.b64encode(b"file2 content").decode("utf-8")},
        ],
    )

    downloaded_files = gitlab.download_files_from_project(
        project_id=1, dir_path="test_dir", branch="main", include_only_files=["^hoodi", "^holesky"]
    )

    expected_paths = [
        os.path.join(os.getcwd(), "tmp", "public_keys", "hoodi-file.txt"),
        os.path.join(os.getcwd(), "tmp", "public_keys", "holesky-file.txt"),
    ]
    assert downloaded_files == expected_paths
    repo_tree_mock.assert_called_once_with(ref="main", path="test_dir", get_all=True)
    repo_blob_mock.assert_has_calls([mocker.call("file_id_1"), mocker.call("file_id_2")])


def test_prepare_temp_directory(gitlab_instance, mocker):
    gitlab, gitlab_mock = gitlab_instance

    # Create a file in tmp/public_keys that should be removed
    remove_this_file = os.path.join("tmp", "public_keys", "this_file_must_be_removed.txt")
    with open(remove_this_file, "w") as f:
        f.write("This file should be removed. If it exists it means GitLab class is broken")

    mocker.patch.object(
        gitlab_mock.projects.get(1),
        "repository_tree",
        return_value=[
            {"id": "file_id_1", "name": "file1.txt", "type": "blob"},
            {"id": "file_id_2", "name": "file2.txt", "type": "blob"},
        ],
    )

    mocker.patch.object(
        gitlab_mock.projects.get(1),
        "repository_blob",
        side_effect=[
            {"content": base64.b64encode(b"file1 content").decode("utf-8")},
            {"content": base64.b64encode(b"file2 content").decode("utf-8")},
        ],
    )

    gitlab.download_files_from_project(project_id=1, dir_path="test_dir", branch="main")

    # Check if only the expected files are present after calling _prepare_temp_directory
    expected_files_after_cleanup = [
        os.path.join("tmp", "public_keys", "file1.txt"),
        os.path.join("tmp", "public_keys", "file2.txt"),
    ]
    assert sorted(os.listdir("tmp/public_keys")) == sorted(
        [os.path.basename(file_path) for file_path in expected_files_after_cleanup]
    )
