"""Aggregate parsed commits into the numbers gitpulse reports."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from gitpulse.git_log import Commit

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _parse_date(date_str: str) -> datetime:
    # Python 3.10's fromisoformat rejects a trailing "Z"; normalize it so the
    # package behaves identically across all supported versions.
    if date_str.endswith(("Z", "z")):
        date_str = date_str[:-1] + "+00:00"
    return datetime.fromisoformat(date_str)


def author_summary(commits: list[Commit]) -> dict[str, dict]:
    summary: dict[str, dict] = defaultdict(
        lambda: {"commits": 0, "insertions": 0, "deletions": 0, "files": set()}
    )
    for commit in commits:
        entry = summary[commit.author]
        entry["commits"] += 1
        entry["insertions"] += commit.insertions
        entry["deletions"] += commit.deletions
        entry["files"].update(f.path for f in commit.files)
    return dict(summary)


def activity_by_weekday(commits: list[Commit]) -> dict[str, int]:
    counts = {name: 0 for name in WEEKDAY_NAMES}
    for commit in commits:
        day = WEEKDAY_NAMES[_parse_date(commit.date).weekday()]
        counts[day] += 1
    return counts


def activity_by_hour(commits: list[Commit]) -> dict[int, int]:
    counts = {hour: 0 for hour in range(24)}
    for commit in commits:
        hour = _parse_date(commit.date).hour
        counts[hour] += 1
    return counts


def top_files(commits: list[Commit], limit: int = 10) -> list[tuple[str, int]]:
    touches: dict[str, int] = defaultdict(int)
    for commit in commits:
        for change in commit.files:
            touches[change.path] += 1
    ranked = sorted(touches.items(), key=lambda item: item[1], reverse=True)
    return ranked[:limit]


def longest_streak(commits: list[Commit]) -> int:
    if not commits:
        return 0
    days = sorted({_parse_date(c.date).date() for c in commits})
    longest = current = 1
    # strict=False is correct here: days[1:] is intentionally one shorter.
    for previous, current_day in zip(days, days[1:], strict=False):
        if (current_day - previous).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def overview(commits: list[Commit], authors: dict[str, dict] | None = None) -> dict:
    total_insertions = sum(c.insertions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    # Callers usually need the per-author breakdown too; let them pass it in
    # rather than walking every commit a second time.
    if authors is None:
        authors = author_summary(commits)
    return {
        "total_commits": len(commits),
        "total_authors": len(authors),
        "total_insertions": total_insertions,
        "total_deletions": total_deletions,
        "longest_streak_days": longest_streak(commits),
    }
