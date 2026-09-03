import csv
import io
import json

import pytest

from gitpulse import __version__
from gitpulse.cli import build_parser, main, run


def test_run_table_format(sample_repo, capsys):
    args = build_parser().parse_args([str(sample_repo)])
    output = run(args)
    assert "gitpulse summary" in output
    assert "Total commits:     3" in output


def test_run_json_format(sample_repo):
    args = build_parser().parse_args([str(sample_repo), "--format", "json"])
    output = run(args)
    parsed = json.loads(output)
    assert parsed["overview"]["total_commits"] == 3


def test_main_returns_error_code_for_non_repo(tmp_path, capsys):
    exit_code = main([str(tmp_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "not a git repository" in captured.err


def test_main_writes_to_output_file(sample_repo, tmp_path):
    out_file = tmp_path / "report.txt"
    exit_code = main([str(sample_repo), "-o", str(out_file)])
    assert exit_code == 0
    assert "gitpulse summary" in out_file.read_text()


def test_negative_top_files_is_rejected(sample_repo, capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([str(sample_repo), "--top-files", "-1"])
    assert exc.value.code == 2
    assert "zero or greater" in capsys.readouterr().err


def test_top_files_zero_hides_the_section(sample_repo):
    args = build_parser().parse_args([str(sample_repo), "--top-files", "0"])
    assert "Top changed files" not in run(args)


def test_json_format_honours_top_files_and_by_hour(sample_repo):
    args = build_parser().parse_args(
        [str(sample_repo), "--format", "json", "--top-files", "1", "--by-hour"]
    )
    parsed = json.loads(run(args))
    assert len(parsed["top_files"]) == 1
    assert "activity_by_hour" in parsed


def test_no_activity_applies_to_markdown_too(sample_repo):
    args = build_parser().parse_args([str(sample_repo), "--format", "markdown", "--no-activity"])
    assert "Activity by weekday" not in run(args)


def test_csv_format_round_trips(sample_repo):
    args = build_parser().parse_args([str(sample_repo), "--format", "csv"])
    rows = list(csv.reader(io.StringIO(run(args))))
    assert rows[0][0] == "section"
    assert any(row[0] == "author" for row in rows)


def test_main_reports_unwritable_output_without_traceback(sample_repo, tmp_path, capsys):
    target = tmp_path / "missing_dir" / "report.txt"
    assert main([str(sample_repo), "-o", str(target)]) == 1
    assert "cannot write" in capsys.readouterr().err


def test_main_writes_utf8_output(tricky_repo, tmp_path):
    out_file = tmp_path / "report.md"
    assert main([str(tricky_repo), "-o", str(out_file), "--format", "markdown"]) == 0
    assert "Zoë Müller" in out_file.read_text(encoding="utf-8")


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_empty_repo_produces_a_zero_report(empty_repo):
    args = build_parser().parse_args([str(empty_repo)])
    assert "Total commits:     0" in run(args)


def test_no_merges_flag_excludes_merge_commits(merge_repo):
    default = json.loads(run(build_parser().parse_args([str(merge_repo), "--format", "json"])))
    filtered = json.loads(
        run(build_parser().parse_args([str(merge_repo), "--format", "json", "--no-merges"]))
    )
    assert default["overview"]["total_commits"] == 4
    assert filtered["overview"]["total_commits"] == 3
