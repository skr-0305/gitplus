"""Command-line entry point for gitpulse."""

from __future__ import annotations

import argparse
import os
import sys

from gitpulse import __version__
from gitpulse.git_log import GitLogError, get_commits, is_git_repo
from gitpulse.render import render_csv, render_json, render_markdown, render_table
from gitpulse.stats import (
    activity_by_hour,
    activity_by_weekday,
    author_summary,
    overview,
    top_files,
)

RENDERERS = {
    "table": render_table,
    "json": render_json,
    "markdown": render_markdown,
    "csv": render_csv,
}


def non_negative_int(value: str) -> int:
    """argparse type for counts that must not be negative.

    Without this, `--top-files -1` was quietly interpreted as the list slice
    `[:-1]`, dropping the last entry instead of reporting a bad argument.
    """
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError(f"must be zero or greater, got {number}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gitpulse", description="Git repository analytics.")
    parser.add_argument("path", nargs="?", default=".", help="Path to a git repository.")
    parser.add_argument("--since", default=None, help="Only include commits after this date.")
    parser.add_argument("--until", default=None, help="Only include commits before this date.")
    parser.add_argument("--author", default=None, help="Filter commits by author.")
    parser.add_argument(
        "--no-merges", action="store_true", help="Exclude merge commits from the stats."
    )
    parser.add_argument(
        "--format",
        choices=sorted(RENDERERS),
        default="table",
        help="Output format.",
    )
    parser.add_argument(
        "--top-files",
        type=non_negative_int,
        default=5,
        help="Number of top files to show (0 to hide).",
    )
    parser.add_argument(
        "--no-activity", action="store_true", help="Hide the weekday activity chart."
    )
    parser.add_argument(
        "--by-hour", action="store_true", help="Also show a commits-per-hour chart."
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Write output to a file instead of stdout."
    )
    parser.add_argument("--version", action="version", version=f"gitpulse {__version__}")
    return parser


def run(args: argparse.Namespace) -> str:
    if not is_git_repo(args.path):
        raise GitLogError(f"{args.path} is not a git repository")

    commits = get_commits(
        args.path,
        since=args.since,
        until=args.until,
        author=args.author,
        no_merges=args.no_merges,
    )
    authors = author_summary(commits)
    stats_overview = overview(commits, authors)

    # These sections used to be assembled only for the table format, so
    # --top-files, --no-activity and --by-hour were silently ignored whenever
    # --format was json or markdown. Build them once and let every renderer
    # decide how to present them.
    weekday = None if args.no_activity else activity_by_weekday(commits)
    hours = activity_by_hour(commits) if args.by_hour else None
    files = top_files(commits, limit=args.top_files) if args.top_files else None

    return RENDERERS[args.format](stats_overview, authors, weekday, hours, files)


def _write_output(result: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(result + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except GitLogError as exc:
        print(f"gitpulse: error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            _write_output(result, args.output)
        except OSError as exc:
            # Previously an unwritable path escaped as a raw traceback.
            print(f"gitpulse: error: cannot write {args.output}: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        print(result)
        sys.stdout.flush()
    except BrokenPipeError:
        # Happens on `gitpulse | head`. Redirect stdout so the interpreter's
        # shutdown flush cannot raise a second time, and exit like a shell would.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 141
    return 0


if __name__ == "__main__":
    sys.exit(main())
