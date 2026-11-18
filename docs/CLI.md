# Command line reference

```
python -m jobsearch [--config PATH] <command> [options]
python /path/to/ai-jobsearch/jobsearch <command> ...        # same thing, from any folder
```

Run from inside your workspace folder, or give `--config PATH` (before the command). Without it the tool walks up from the current folder to find `jobsearch.config.json`; `JOBSEARCH_CONFIG` can also point at one. `python -m jobsearch <command> -h` lists a command's options.

**Exit codes:** `0` done; `1` finished, but something needs your action (config errors, a refused status change, an adjustment that matched nothing, duplicates found, a do-not-claim term in a resume); `2` could not run (bad arguments, missing file, no config).

The tools never touch the network and never write outside the workspace paths you pass or the config names.

## The search run, in order

| Step | Command | Reads | Writes |
|---|---|---|---|
| 0 | `check` | config | nothing; prints a summary, warnings and errors |
| 1 | `queries [--source S] [--batch B] [--pending]` / `--plan` / `--mark LABEL --status DONE` | config | `<search>/state/staged_run.json` only with `--mark` |
| 2 | `extract --raw DIR --out DIR [--date D]` | `DIR/*.json` raw rows | `keep.json`, `dropped.json` in `--out` |
| 3 | `score keep.json [--date D] [--out F]` | keep.json | `scored.json` beside the input |
| 4 | `adjust scored.json adjustments.json [--out F]` | both | scored.json (or `--out`) with an `adjustments` history per row |
| 5 | `liveness scored.json [--date D]` | scored.json | `scored_live.json`, `dropped_live.json` |
| 6 | `seen annotate scored_live.json` | seen store | adds `is_new`, `times_seen`, `first_seen` to the rows |
| 7 | `dashboard scored_live.json --dropped dropped.json dropped_live.json [--date D] [--sources ...] [--unavailable ...] [--quick] [--notes TEXT] [--csv] [--out DIR]` | scored rows, tracker | `job_search_<date>.html` (+ `.csv`) |
| 8 | `seen ingest scored_live.json --run N [--date D] [--filtered dropped.json]` | | `<search>/state/seen_jobs.json` |
| 9 | `seen report [--run N]` | seen store | prints new, repeat and held roles |

`liveness --held` and `seen held` list held roles and the LinkedIn batches to re-run so the search itself shows they are still open. `seen hold|unhold --ids li:0000000101 ...` marks or releases a posting you are waiting on.

Run numbers: the dashboard counts the `job_search_*.html` files already in the search folder. Rebuilding the same day's dashboard keeps that day's number.

## Tracker

| Command | Does |
|---|---|
| `tracker report [--date D]` | counts by status; applications 14 or more days old with no recorded outcome |
| `tracker match --company C --title T [--link URL]` | the prior application a posting resembles (posting id first, then company plus two distinctive title words on applied entries) |
| `tracker dupes --jd FILE [--company C] [--title T] [--req-id R] [--link URL]` | prior entries with the same requisition or posting id, and saved JDs at or above 85% text similarity. Exit 1 if any |
| `tracker add --company C --title T [--id X] [--jd-file F] [--folder F] [--keywords K ...] [--req-id R] [--source-job-id J] [--note N]` | a new entry: `status: drafted`, `applied: false` |
| `tracker update --id X [--status S] [--applied] [--applied-date D] [--outcome O] [--note N] --confirmed` | records a status you confirmed. Without `--confirmed` it is refused (exit 1). Statuses: drafted, applied, screen, interview, offer, declined, closed, passed |

## Resume tools

| Command | Does |
|---|---|
| `ats RESUME.docx JD.txt [--md FILE]` | parse-safety (text boxes, images, tables, headers, standard headings, contact details), JD keyword coverage and gaps, a DO NOT ADD list, and a guard for do-not-claim terms inside the resume. Exit 1 if the resume contains a do-not-claim term |
| `gaps report [--out DIR]` | `skill_gap_report.html` and `.json`: each `skill_vocabulary` item against saved JDs and ingested scrapes, status Claimed / Decided no / Gap |
| `gaps ingest scored_live.json --run N [--min-score 65]` | stores the matched skill terms (not the posting text) of strong-fit rows |

## Environment

| Variable | Effect |
|---|---|
| `JOBSEARCH_CONFIG` | path to the config when `--config` is not given and none is found above the current folder |

## Running without Claude

Everything above works from a terminal. `examples/run_demo.py` strings the steps together on the fictional workspace; reading it is the quickest way to see a complete run.
