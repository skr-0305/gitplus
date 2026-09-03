"""Read `git log` output and parse it into structured commit records."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field

RECORD_SEP = "\x02"
FIELD_SEP = "\x1f"
HEADER_END = "\x03"
LOG_FORMAT = f"{RECORD_SEP}%H{FIELD_SEP}%an{FIELD_SEP}%ae{FIELD_SEP}%ad{FIELD_SEP}%s{HEADER_END}"

# Matches the brace form git uses for renames, e.g. "src/{old => new}/mod.py".
_BRACED_RENAME = re.compile(r"\{(?P<old>[^{}]*) => (?P<new>[^{}]*)\}")

# `git log` refuses to run on a repository whose HEAD has no commits yet. We
# probe for that case explicitly so callers get an empty result instead of an
# error, without having to match on localized git messages.
_HEAD_PROBE = ["git", "rev-parse", "--quiet", "--verify", "HEAD"]


class GitLogError(RuntimeError):
    pass


@dataclass
class FileChange:
    path: str
    insertions: int
    deletions: int


@dataclass
class Commit:
    commit_hash: str
    author: str
    email: str
    date: str
    subject: str
    files: list[FileChange] = field(default_factory=list)

    @property
    def insertions(self) -> int:
        return sum(f.insertions for f in self.files)

    @property
    def deletions(self) -> int:
        return sum(f.deletions for f in self.files)


def _run(args: list[str], cwd: str) -> str:
    # Check the directory first: without this, a missing `cwd` makes subprocess
    # raise FileNotFoundError, which is indistinguishable from a missing git
    # binary and produced a very misleading error message.
    if not os.path.isdir(cwd):
        raise GitLogError(f"{cwd}: no such directory")
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            # Decode as UTF-8 explicitly rather than relying on the locale, so
            # non-ASCII author names and paths survive on any machine.
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except FileNotFoundError as exc:
        raise GitLogError("git executable not found; is git installed and on PATH?") from exc
    except PermissionError as exc:
        raise GitLogError(f"{cwd}: permission denied") from exc
    except subprocess.CalledProcessError as exc:
        raise GitLogError((exc.stderr or "").strip() or "git command failed") from exc
    return result.stdout


def normalize_path(path: str) -> str:
    """Collapse a numstat rename marker down to the post-rename path.

    git reports renames as ``old.py => new.py`` or ``src/{old => new}/mod.py``.
    Left as-is these become phantom entries that never match the real file, so
    a renamed file's history gets split across two names in the file rankings.
    """
    if " => " not in path:
        return path
    if "{" in path:
        collapsed = _BRACED_RENAME.sub(lambda m: m.group("new"), path)
        # "a/{b => }/c.py" collapses to "a//c.py"; tidy up the empty segment.
        return "/".join(part for part in collapsed.split("/") if part) or path
    return path.split(" => ", 1)[1]


def _parse_numstat_line(line: str) -> FileChange | None:
    parts = line.split("\t")
    if len(parts) != 3:
        return None
    added_raw, deleted_raw, path = parts
    # Binary files are reported as "-" for both counts.
    try:
        added = 0 if added_raw == "-" else int(added_raw)
        deleted = 0 if deleted_raw == "-" else int(deleted_raw)
    except ValueError:
        return None
    return FileChange(path=normalize_path(path), insertions=added, deletions=deleted)


def parse_log_output(raw: str) -> list[Commit]:
    commits: list[Commit] = []
    for chunk in raw.split(RECORD_SEP):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        header, _, body = chunk.partition(HEADER_END)
        fields = header.split(FIELD_SEP)
        if len(fields) != 5:
            continue
        commit_hash, author, email, date, subject = fields
        files = []
        for line in body.strip("\n").split("\n"):
            if not line:
                continue
            change = _parse_numstat_line(line)
            if change is not None:
                files.append(change)
        commits.append(
            Commit(
                commit_hash=commit_hash,
                author=author,
                email=email,
                date=date,
                subject=subject,
                files=files,
            )
        )
    return commits


def has_commits(repo_path: str) -> bool:
    """True if HEAD points at at least one commit."""
    try:
        return bool(_run(_HEAD_PROBE, cwd=repo_path).strip())
    except GitLogError:
        return False


def get_commits(
    repo_path: str,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
    no_merges: bool = False,
) -> list[Commit]:
    args = [
        "git",
        # Keep UTF-8 paths readable instead of octal-escaped ("caf\303\251.txt").
        "-c",
        "core.quotePath=false",
        "log",
        "--date=iso-strict",
        "--numstat",
        f"--pretty=format:{LOG_FORMAT}",
    ]
    if no_merges:
        args.append("--no-merges")
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if author:
        args.append(f"--author={author}")
    try:
        raw = _run(args, cwd=repo_path)
    except GitLogError:
        # `git log` errors out on a repository whose HEAD has no commits yet.
        # That is an empty repo, not a failure -- but anything else still is.
        if is_git_repo(repo_path) and not has_commits(repo_path):
            return []
        raise
    return parse_log_output(raw)


def is_git_repo(path: str) -> bool:
    # `--is-inside-work-tree` prints "false" (and still exits 0) for bare
    # repositories, so it never actually answered the question being asked.
    # `--git-dir` succeeds for both bare and normal repos, which is what we want.
    try:
        _run(["git", "rev-parse", "--git-dir"], cwd=path)
        return True
    except GitLogError:
        return False
