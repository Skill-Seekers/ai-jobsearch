# Demo walkthrough

One command runs a complete search on the fictional workspace. No accounts, no network, nothing installed.

```
python examples/run_demo.py            # builds a temp workspace, runs every step, prints the dashboard path
python examples/run_demo.py my-demo    # or choose a folder (it refuses to overwrite)
```

The candidate is "Alex Rivera", a fictional TPM in Austin. The 19 raw rows in `examples/sample-workspace/search/raw/2026-10-26/` stand for what the connectors would return on the sample date 2026-10-26. Every employer, posting and number is invented, and posting ids start `0000`.

## What each step shows

| Step | What happens to the sample data |
|---|---|
| `check` | Validates the config and prints a summary |
| `extract` | 19 rows become 17 unique (the Indeed and Glassdoor copies of a LinkedIn role merge); one is older than 7 days; **10 kept, 6 removed**: an excluded company (listed in the Filtered tab with its reason), a company marked silent (listed nowhere), a staffing agency, a "Scrum Master" title, a Boston onsite role, and a role paying at most $110,000 |
| `score` | 10 rows scored; six land in the 90s, so the saturation warning fires; an ML-platform role is **scope-gated to Stretch / Watch** despite scoring 77 |
| `adjust` | One recorded adjustment with its reason, as the skill would after reading a description |
| `liveness` | Two postings leave: one whose text says "This position has been filled", one whose apply-by date (Oct 20) has passed |
| `dashboard` | `job_search_2026-10-26.html` (and a CSV because of `--csv`): 8 results, 7 in the Filtered tab (five from `extract`, two from `liveness`), the tracker's applications on a third tab, and a Tailspin role already marked as applied |
| `seen ingest` / `seen report` | The first run: every posting is new. Run it again on a second day and previous postings show as seen before |
| `ats` | The sample resume parses cleanly; keyword gaps are listed; `pmp` and `six sigma black belt` appear under DO NOT ADD because the sample config rules them out |
| `gaps` | `skill_gap_report.html`: each skill against the saved JDs and the sample resume, marked Claimed, Decided no, or Gap |

## Things to try next

- Edit `jobsearch.config.json` in the demo workspace: move a company between tiers, change `posted_within_days`, add a title exclusion. Re-run the steps and watch the dashboard change.
- Add `"outputs": {"csv": true}` and open the CSV in a spreadsheet app.
- Make a copy of the sample workspace, replace the config's role sections following [ADAPTING](ADAPTING.md), and score the same rows as another role to see the scope gate and families change the ranking.
- Run `python -m jobsearch --config <workspace>/jobsearch.config.json tracker update --id tailspin-cloud-tpm --status screen` and see it refuse; add `--confirmed` and see the status recorded.
