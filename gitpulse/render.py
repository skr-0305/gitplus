"""Turn aggregated stats into the various output formats."""

from __future__ import annotations

import csv
import io
import json

SECTION_WIDTH = 40


def _sorted_authors(authors: dict[str, dict]) -> list[tuple[str, dict]]:
    # Sort by commits, then by name so equal counts have a stable order
    # instead of depending on dict insertion order.
    return sorted(authors.items(), key=lambda kv: (-kv[1]["commits"], kv[0]))


def render_bar_chart(data: dict, width: int = 30) -> str:
    if not data:
        return ""
    max_value = max(data.values()) or 1
    label_width = max(len(str(label)) for label in data)
    lines = []
    for label, value in data.items():
        bar_len = int((value / max_value) * width)
        # Never render a non-zero bucket as an empty bar; on a wide range that
        # made small-but-real activity look like no activity at all.
        if value > 0:
            bar_len = max(bar_len, 1)
        lines.append(f"{str(label):>{label_width}} | {'#' * bar_len} {value}")
    return "\n".join(lines)


def _overview_lines(overview: dict) -> list[str]:
    return [
        f"Total commits:     {overview['total_commits']}",
        f"Total authors:     {overview['total_authors']}",
        f"Total insertions:  {overview['total_insertions']}",
        f"Total deletions:   {overview['total_deletions']}",
        f"Longest streak:    {overview['longest_streak_days']} day(s)",
    ]


def _section(title: str, body: str) -> list[str]:
    return ["", title, "-" * SECTION_WIDTH, body]


def render_table(
    overview: dict,
    authors: dict,
    weekday: dict | None = None,
    hours: dict | None = None,
    files: list[tuple[str, int]] | None = None,
) -> str:
    lines = ["gitpulse summary", "-" * SECTION_WIDTH, *_overview_lines(overview)]

    if authors:
        # Size the name column to the data. A fixed 20 chars silently broke
        # alignment for any contributor with a longer name.
        name_width = max(len("Author"), max(len(name) for name in authors))
        rows = [f"{'Author':<{name_width}}{'Commits':>10}{'Insert':>10}{'Delete':>10}"]
        for author, data in _sorted_authors(authors):
            rows.append(
                f"{author:<{name_width}}{data['commits']:>10}"
                f"{data['insertions']:>10}{data['deletions']:>10}"
            )
        lines += _section("By author", "\n".join(rows))

    if weekday:
        lines += _section("Activity by weekday", render_bar_chart(weekday))
    if hours:
        lines += _section("Activity by hour", render_bar_chart(hours))
    if files:
        body = "\n".join(f"{count:>4}  {path}" for path, count in files)
        lines += _section("Top changed files", body)

    return "\n".join(lines)


def render_markdown(
    overview: dict,
    authors: dict,
    weekday: dict | None = None,
    hours: dict | None = None,
    files: list[tuple[str, int]] | None = None,
) -> str:
    lines = [
        "# gitpulse summary",
        "",
        f"- **Total commits:** {overview['total_commits']}",
        f"- **Total authors:** {overview['total_authors']}",
        f"- **Total insertions:** {overview['total_insertions']}",
        f"- **Total deletions:** {overview['total_deletions']}",
        f"- **Longest streak:** {overview['longest_streak_days']} day(s)",
        "",
        "## By author",
        "",
        "| Author | Commits | Insertions | Deletions |",
        "|---|---|---|---|",
    ]
    for author, data in _sorted_authors(authors):
        lines.append(
            f"| {author} | {data['commits']} | {data['insertions']} | {data['deletions']} |"
        )

    if weekday:
        lines += ["", "## Activity by weekday", "", "| Day | Commits |", "|---|---|"]
        lines += [f"| {day} | {count} |" for day, count in weekday.items()]
    if hours:
        lines += ["", "## Activity by hour", "", "| Hour | Commits |", "|---|---|"]
        lines += [f"| {hour:02d} | {count} |" for hour, count in hours.items()]
    if files:
        lines += ["", "## Top changed files", "", "| File | Changes |", "|---|---|"]
        lines += [f"| `{path}` | {count} |" for path, count in files]

    return "\n".join(lines)


def render_json(
    overview: dict,
    authors: dict,
    weekday: dict | None = None,
    hours: dict | None = None,
    files: list[tuple[str, int]] | None = None,
) -> str:
    payload: dict = {
        "overview": overview,
        "authors": {
            name: {**data, "files": sorted(data.get("files", ()))}
            for name, data in authors.items()
        },
    }
    if weekday is not None:
        payload["activity_by_weekday"] = weekday
    if hours is not None:
        # JSON object keys must be strings; be explicit rather than letting
        # json coerce the integer hours behind our back.
        payload["activity_by_hour"] = {str(hour): count for hour, count in hours.items()}
    if files is not None:
        payload["top_files"] = [{"path": path, "changes": count} for path, count in files]
    return json.dumps(payload, indent=2)


def render_csv(
    overview: dict,
    authors: dict,
    weekday: dict | None = None,
    hours: dict | None = None,
    files: list[tuple[str, int]] | None = None,
) -> str:
    buffer = io.StringIO()
    # newline="" is handled by writing to StringIO with explicit \n terminators.
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["section", "key", "commits", "insertions", "deletions"])
    for field, value in overview.items():
        writer.writerow(["overview", field, value, "", ""])
    for author, data in _sorted_authors(authors):
        writer.writerow(
            ["author", author, data["commits"], data["insertions"], data["deletions"]]
        )
    for day, count in (weekday or {}).items():
        writer.writerow(["weekday", day, count, "", ""])
    for hour, count in (hours or {}).items():
        writer.writerow(["hour", f"{hour:02d}", count, "", ""])
    for path, count in files or []:
        writer.writerow(["file", path, count, "", ""])
    return buffer.getvalue().rstrip("\n")
