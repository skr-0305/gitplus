import subprocess

import pytest

from gitpulse.git_log import (
    GitLogError,
    get_commits,
    is_git_repo,
    normalize_path,
    parse_log_output,
)


def test_is_git_repo_true(sample_repo):
    assert is_git_repo(str(sample_repo)) is True


def test_is_git_repo_false(tmp_path):
    assert is_git_repo(str(tmp_path)) is False


def test_get_commits_returns_all_commits_in_order(sample_repo):
    commits = get_commits(str(sample_repo))
    subjects = [c.subject for c in commits]
    assert subjects == ["update a.txt", "add b.txt", "add a.txt"]


def test_get_commits_filters_by_author(sample_repo):
    commits = get_commits(str(sample_repo), author="Bob")
    assert len(commits) == 1
    assert commits[0].author == "Bob"


def test_commit_insertions_and_deletions(sample_repo):
    commits = get_commits(str(sample_repo))
    update_commit = next(c for c in commits if c.subject == "update a.txt")
    assert update_commit.insertions == 1
    assert update_commit.deletions == 1


def test_get_commits_raises_on_non_repo(tmp_path):
    with pytest.raises(GitLogError):
        get_commits(str(tmp_path))


def test_parse_log_output_empty_string():
    assert parse_log_output("") == []


def test_parse_log_output_ignores_malformed_chunk():
    raw = "\x02badheader\x03\n"
    assert parse_log_output(raw) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("plain.py", "plain.py"),
        ("old.txt => new.txt", "new.txt"),
        ("src/{old => new}/mod.py", "src/new/mod.py"),
        ("src/{ => nested}/mod.py", "src/nested/mod.py"),
        ("src/{nested => }/mod.py", "src/mod.py"),
        ("weird => spaced => name.py", "spaced => name.py"),
    ],
)
def test_normalize_path_collapses_renames(raw, expected):
    assert normalize_path(raw) == expected


def test_rename_is_attributed_to_the_new_path(tricky_repo):
    commits = get_commits(str(tricky_repo))
    rename = next(c for c in commits if c.subject == "rename old.txt")
    assert [f.path for f in rename.files] == ["new.txt"]


def test_non_ascii_paths_and_authors_are_not_escaped(tricky_repo):
    commits = get_commits(str(tricky_repo))
    paths = {f.path for c in commits for f in c.files}
    assert "café.txt" in paths
    assert any(c.author == "Zoë Müller" for c in commits)


def test_binary_files_count_as_zero_lines(tricky_repo):
    commits = get_commits(str(tricky_repo))
    binary = next(c for c in commits if c.subject == "add binary")
    change = next(f for f in binary.files if f.path == "blob.bin")
    assert (change.insertions, change.deletions) == (0, 0)


def test_empty_repo_returns_no_commits(empty_repo):
    assert get_commits(str(empty_repo)) == []


def test_is_git_repo_true_for_bare_repo(sample_repo, tmp_path):
    bare = tmp_path / "bare.git"
    subprocess.run(
        ["git", "clone", "--bare", str(sample_repo), str(bare)],
        check=True,
        capture_output=True,
    )
    assert is_git_repo(str(bare)) is True


def test_missing_directory_reports_a_useful_error(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(GitLogError, match="no such directory"):
        get_commits(str(missing))


def test_parse_log_output_skips_unparsable_numstat_counts():
    raw = "\x02h\x1fA\x1fa@e.com\x1f2024-01-01T00:00:00+00:00\x1fsubj\x03\nx\ty\tf.py\n"
    commits = parse_log_output(raw)
    assert len(commits) == 1
    assert commits[0].files == []
