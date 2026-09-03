# gitpulse

Command-line analytics for any git repository. Point it at a repo and get commit
counts, insertions/deletions per author, activity heatmaps, longest contribution
streaks, and the files that change the most — all from local git history, no
network access or third-party services required.

## Install

```bash
pip install -e .
```

Requires Python 3.10+ and git available on your `PATH`.

## Usage

```bash
gitpulse                          # analyze the current directory
gitpulse /path/to/repo            # analyze a specific repo
gitpulse --since "2024-01-01"     # only commits after a date
gitpulse --author "Jane Doe"      # filter by author
gitpulse --until "2024-06-01"     # only commits before a date
gitpulse --author "Jane Doe"      # filter by author
gitpulse --no-merges              # ignore merge commits
gitpulse --format json            # table / json / markdown / csv
gitpulse --top-files 10           # show more hot files (0 hides the section)
gitpulse --by-hour                # add a commits-per-hour chart
gitpulse --no-activity            # hide the weekday chart
gitpulse -o report.md --format markdown   # write a markdown report to a file
gitpulse --version
```

`--top-files`, `--by-hour` and `--no-activity` apply to every output format, so
a JSON or CSV report contains the same sections as the terminal one.

### Example output

```
gitpulse summary
----------------------------------------
Total commits:     128
Total authors:     4
Total insertions:  5321
Total deletions:   1904
Longest streak:    9 day(s)

By author
----------------------------------------
Author              Commits    Insert    Delete
Alice                    64      3012      1100
Bob                      40      1600       500
...

Activity by weekday
----------------------------------------
Mon  | ################## 18
Tue  | ###################### 22
Wed  | ############# 13
...

Top changed files
----------------------------------------
  42  gitpulse/cli.py
  31  gitpulse/stats.py
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

`--format csv` writes one row per record with a `section` column
(`overview`, `author`, `weekday`, `hour`, `file`), which imports cleanly into a
spreadsheet and pivots without further cleanup.

## Notes

- Timestamps are read in each commit's own timezone, so the weekday and hour
  charts reflect the author's local working hours rather than UTC.
- Renamed files are attributed to their new path, so a rename does not split a
  file's history across two entries in the rankings.
- Authors are grouped by name. Someone who commits under two different names
  will appear twice.

## Roadmap

- [x] CSV export (`--format csv`) for spreadsheet-friendly reports
- [ ] Per-file contributor breakdown
- [ ] Configurable date bucketing for the activity chart (daily/weekly/monthly)
- [ ] Group authors by email, with a `.mailmap`-aware fallback

## License

MIT
