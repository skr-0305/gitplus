import csv
import io
import json

from gitpulse.render import (
    render_bar_chart,
    render_csv,
    render_json,
    render_markdown,
    render_table,
)

OVERVIEW = {
    "total_commits": 2,
    "total_authors": 1,
    "total_insertions": 10,
    "total_deletions": 2,
    "longest_streak_days": 2,
}
AUTHORS = {
    "Alice": {"commits": 2, "insertions": 10, "deletions": 2, "files": {"a.txt"}},
}


def test_render_table_contains_key_figures():
    output = render_table(OVERVIEW, AUTHORS)
    assert "Total commits:     2" in output
    assert "Alice" in output


def test_render_markdown_has_table_header():
    output = render_markdown(OVERVIEW, AUTHORS)
    assert "| Author | Commits | Insertions | Deletions |" in output
    assert "Alice" in output


def test_render_json_round_trips():
    output = render_json(OVERVIEW, AUTHORS)
    parsed = json.loads(output)
    assert parsed["overview"]["total_commits"] == 2
    assert parsed["authors"]["Alice"]["files"] == ["a.txt"]


def test_render_bar_chart_scales_to_width():
    chart = render_bar_chart({"Mon": 5, "Tue": 10}, width=10)
    lines = chart.split("\n")
    assert lines[1].count("#") == 10
    assert lines[0].count("#") == 5


def test_render_bar_chart_empty():
    assert render_bar_chart({}) == ""


LONG_AUTHORS = {
    "A-Very-Long-Contributor-Name": {
        "commits": 3,
        "insertions": 10,
        "deletions": 2,
        "files": {"a.txt"},
    },
    "Bo": {"commits": 1, "insertions": 1, "deletions": 0, "files": {"b.txt"}},
}
WEEKDAY = {"Mon": 5, "Tue": 0, "Wed": 1}
HOURS = {9: 4, 10: 2}
FILES = [("a.txt", 3), ("b.txt", 1)]


def test_render_table_columns_stay_aligned_for_long_names():
    lines = render_table(OVERVIEW, LONG_AUTHORS).splitlines()
    rows = [line for line in lines if line.startswith(("Author", "A-Very", "Bo "))]
    assert len({len(row) for row in rows}) == 1, rows


def test_render_table_includes_optional_sections():
    output = render_table(OVERVIEW, AUTHORS, WEEKDAY, HOURS, FILES)
    assert "Activity by weekday" in output
    assert "Activity by hour" in output
    assert "Top changed files" in output


def test_render_bar_chart_never_hides_a_nonzero_bucket():
    chart = render_bar_chart({"Mon": 100, "Tue": 1}, width=10)
    tue = [line for line in chart.splitlines() if line.startswith("Tue")][0]
    assert tue.count("#") == 1


def test_render_bar_chart_leaves_zero_buckets_empty():
    chart = render_bar_chart({"Mon": 10, "Tue": 0}, width=10)
    tue = [line for line in chart.splitlines() if line.startswith("Tue")][0]
    assert tue.count("#") == 0


def test_authors_sort_by_commits_then_name():
    authors = {
        "Zoe": {"commits": 2, "insertions": 0, "deletions": 0, "files": set()},
        "Adam": {"commits": 2, "insertions": 0, "deletions": 0, "files": set()},
    }
    output = render_markdown(OVERVIEW, authors)
    assert output.index("| Adam |") < output.index("| Zoe |")


def test_render_json_includes_optional_sections():
    parsed = json.loads(render_json(OVERVIEW, AUTHORS, WEEKDAY, HOURS, FILES))
    assert parsed["activity_by_weekday"]["Mon"] == 5
    assert parsed["activity_by_hour"]["9"] == 4
    assert parsed["top_files"][0] == {"path": "a.txt", "changes": 3}


def test_render_json_omits_sections_that_were_not_requested():
    parsed = json.loads(render_json(OVERVIEW, AUTHORS))
    assert "top_files" not in parsed
    assert "activity_by_weekday" not in parsed


def test_render_markdown_includes_optional_sections():
    output = render_markdown(OVERVIEW, AUTHORS, WEEKDAY, HOURS, FILES)
    assert "## Top changed files" in output
    assert "| `a.txt` | 3 |" in output


def test_render_csv_is_parsable_and_covers_every_section():
    rows = list(csv.reader(io.StringIO(render_csv(OVERVIEW, AUTHORS, WEEKDAY, HOURS, FILES))))
    assert rows[0] == ["section", "key", "commits", "insertions", "deletions"]
    sections = {row[0] for row in rows[1:]}
    assert sections == {"overview", "author", "weekday", "hour", "file"}


def test_render_csv_quotes_commas_in_names():
    authors = {"Doe, Jane": {"commits": 1, "insertions": 0, "deletions": 0, "files": set()}}
    output = render_csv(OVERVIEW, authors)
    assert '"Doe, Jane"' in output
    rows = list(csv.reader(io.StringIO(output)))
    assert ["author", "Doe, Jane", "1", "0", "0"] in rows
