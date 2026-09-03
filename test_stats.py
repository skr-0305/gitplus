from gitpulse.git_log import Commit, FileChange
from gitpulse.stats import (
    activity_by_hour,
    activity_by_weekday,
    author_summary,
    longest_streak,
    overview,
    top_files,
)


def make_commit(commit_hash, author, date, files=None):
    return Commit(
        commit_hash=commit_hash,
        author=author,
        email=f"{author.lower()}@example.com",
        date=date,
        subject=f"commit {commit_hash}",
        files=files or [],
    )


def test_author_summary_counts_commits_and_lines():
    commits = [
        make_commit("1", "Alice", "2024-01-01T09:00:00+00:00", [FileChange("a.txt", 5, 1)]),
        make_commit("2", "Alice", "2024-01-02T09:00:00+00:00", [FileChange("b.txt", 2, 0)]),
        make_commit("3", "Bob", "2024-01-03T09:00:00+00:00", [FileChange("a.txt", 0, 3)]),
    ]
    summary = author_summary(commits)
    assert summary["Alice"]["commits"] == 2
    assert summary["Alice"]["insertions"] == 7
    assert summary["Bob"]["deletions"] == 3
    assert summary["Alice"]["files"] == {"a.txt", "b.txt"}


def test_activity_by_weekday():
    commits = [
        make_commit("1", "Alice", "2024-01-01T09:00:00+00:00"),
        make_commit("2", "Bob", "2024-01-01T10:00:00+00:00"),
    ]
    counts = activity_by_weekday(commits)
    assert counts["Mon"] == 2


def test_activity_by_hour():
    commits = [
        make_commit("1", "Alice", "2024-01-01T09:00:00+00:00"),
        make_commit("2", "Bob", "2024-01-01T09:30:00+00:00"),
    ]
    counts = activity_by_hour(commits)
    assert counts[9] == 2


def test_top_files_ranks_by_touch_count():
    commits = [
        make_commit("1", "Alice", "2024-01-01T09:00:00+00:00", [FileChange("a.txt", 1, 0)]),
        make_commit("2", "Bob", "2024-01-02T09:00:00+00:00", [FileChange("a.txt", 1, 0)]),
        make_commit("3", "Bob", "2024-01-03T09:00:00+00:00", [FileChange("b.txt", 1, 0)]),
    ]
    ranked = top_files(commits, limit=1)
    assert ranked == [("a.txt", 2)]


def test_longest_streak_with_gaps():
    commits = [
        make_commit("1", "Alice", "2024-01-01T09:00:00+00:00"),
        make_commit("2", "Alice", "2024-01-02T09:00:00+00:00"),
        make_commit("3", "Alice", "2024-01-04T09:00:00+00:00"),
        make_commit("4", "Alice", "2024-01-05T09:00:00+00:00"),
        make_commit("5", "Alice", "2024-01-06T09:00:00+00:00"),
    ]
    assert longest_streak(commits) == 3


def test_longest_streak_empty():
    assert longest_streak([]) == 0


def test_overview_totals():
    commits = [
        make_commit("1", "Alice", "2024-01-01T09:00:00+00:00", [FileChange("a.txt", 5, 1)]),
        make_commit("2", "Bob", "2024-01-02T09:00:00+00:00", [FileChange("b.txt", 2, 0)]),
    ]
    result = overview(commits)
    assert result["total_commits"] == 2
    assert result["total_authors"] == 2
    assert result["total_insertions"] == 7
    assert result["total_deletions"] == 1


def test_overview_accepts_a_precomputed_author_summary():
    commits = [make_commit("1", "Alice", "2024-01-01T09:00:00+00:00", [FileChange("a.txt", 5, 1)])]
    authors = author_summary(commits)
    assert overview(commits, authors) == overview(commits)


def test_dates_with_zulu_suffix_are_supported():
    commits = [make_commit("1", "Alice", "2024-01-01T09:00:00Z")]
    assert activity_by_weekday(commits)["Mon"] == 1
    assert activity_by_hour(commits)[9] == 1
