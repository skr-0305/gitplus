import subprocess
from pathlib import Path

import pytest


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.name", "Alice"], cwd=repo)
    _run(["git", "config", "user.email", "alice@example.com"], cwd=repo)

    (repo / "a.txt").write_text("hello\n")
    _run(["git", "add", "a.txt"], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Alice",
            "-c",
            "user.email=alice@example.com",
            "commit",
            "-m",
            "add a.txt",
            "--date=2024-01-01T09:00:00",
        ],
        cwd=repo,
    )

    (repo / "b.txt").write_text("world\n")
    _run(["git", "add", "b.txt"], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Bob",
            "-c",
            "user.email=bob@example.com",
            "commit",
            "-m",
            "add b.txt",
            "--date=2024-01-02T14:30:00",
        ],
        cwd=repo,
    )

    (repo / "a.txt").write_text("hello again\n")
    _run(["git", "add", "a.txt"], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Alice",
            "-c",
            "user.email=alice@example.com",
            "commit",
            "-m",
            "update a.txt",
            "--date=2024-01-03T10:15:00",
        ],
        cwd=repo,
    )

    return repo


@pytest.fixture
def tricky_repo(tmp_path: Path) -> Path:
    """A repo exercising renames, binary files and non-ASCII names."""
    repo = tmp_path / "tricky_repo"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    _run(["git", "config", "user.name", "Alice"], cwd=repo)
    _run(["git", "config", "user.email", "alice@example.com"], cwd=repo)

    (repo / "old.txt").write_text("hello\n")
    (repo / "café.txt").write_text("unicode\n")
    _run(["git", "add", "-A"], cwd=repo)
    _run(["git", "commit", "-m", "initial", "--date=2024-03-01T09:00:00"], cwd=repo)

    _run(["git", "mv", "old.txt", "new.txt"], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Zoë Müller",
            "-c",
            "user.email=zoe@example.com",
            "commit",
            "-m",
            "rename old.txt",
            "--date=2024-03-02T09:00:00",
        ],
        cwd=repo,
    )

    (repo / "blob.bin").write_bytes(bytes(range(256)) * 8)
    _run(["git", "add", "-A"], cwd=repo)
    _run(["git", "commit", "-m", "add binary", "--date=2024-03-03T09:00:00"], cwd=repo)
    return repo


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """An initialised repo with no commits yet (unborn HEAD)."""
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    _run(["git", "init"], cwd=repo)
    return repo


@pytest.fixture
def merge_repo(tmp_path: Path) -> Path:
    """A repo whose history contains a real merge commit."""
    repo = tmp_path / "merge_repo"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], cwd=repo)
    _run(["git", "config", "user.name", "Alice"], cwd=repo)
    _run(["git", "config", "user.email", "alice@example.com"], cwd=repo)

    (repo / "base.txt").write_text("base\n")
    _run(["git", "add", "-A"], cwd=repo)
    _run(["git", "commit", "-m", "base", "--date=2024-04-01T09:00:00"], cwd=repo)

    _run(["git", "checkout", "-q", "-b", "feature"], cwd=repo)
    (repo / "feature.txt").write_text("feature\n")
    _run(["git", "add", "-A"], cwd=repo)
    _run(["git", "commit", "-m", "feature work", "--date=2024-04-02T09:00:00"], cwd=repo)

    _run(["git", "checkout", "-q", "main"], cwd=repo)
    (repo / "base.txt").write_text("base changed\n")
    _run(["git", "add", "-A"], cwd=repo)
    _run(["git", "commit", "-m", "main work", "--date=2024-04-02T10:00:00"], cwd=repo)

    _run(["git", "merge", "--no-ff", "-m", "merge feature", "feature"], cwd=repo)
    return repo
