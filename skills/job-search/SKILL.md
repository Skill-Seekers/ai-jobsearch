---
name: job-search
description: Runs a multi-source job search (LinkedIn, Indeed, Glassdoor, Dice when connected), scores each role with a transparent keyword heuristic plus a scope gate, drops closed postings, remembers what earlier runs saw, and builds an HTML dashboard (CSV optional) with the application tracker alongside. Use when the user says "find me jobs", "run the job search", "what's new on the job market", "search for roles", or asks for any role discovery.
---

# Job Search

Find active roles, score them honestly, and give the candidate one dashboard. The `jobsearch` command line does the deterministic work (filtering, scoring, de-duplication, closed-posting checks, memory, the dashboard). You do the connector calls, read the descriptions that matter, and record any score change with a reason.

Role-specific judgement lives in `references/role-profile.md` (the shipped example is a Technical Program Manager; for another role it is replaced, see `docs/ADAPTING.md`).

## Setup

Run tools with `python3 <plugin root>/jobsearch <command>` from inside the workspace folder (`<plugin root>` is `${CLAUDE_PLUGIN_ROOT}` when set, otherwise the folder two levels above this skill's base directory, the one that holds `skills/` and `jobsearch/`). Full list: `docs/CLI.md`. File formats: `docs/DATA_SCHEMAS.md`.

Pre-flight, in order:

1. `check`. If the config is missing, run the `setup-workspace` skill. Stop on any ERROR.
2. **Confirm the sources are connected.** This suite connects to nothing itself: the candidate must have connected Apify (LinkedIn, Glassdoor, Dice actors) and/or the Indeed connector beforehand. Check what the session has. If nothing is available, stop and say what to connect (`docs/INSTRUCTIONS.md`, Prerequisites). Never substitute guesses, sample data or other scraping. If only some are available, run those and list the rest as unavailable.
3. `tracker report` for context, then `seen stats`.
4. Pick the run mode. Full is the default. **Quick** (the user says quick, short, test, smoke test): two sources, one query each, result limit 10, no company batches; pass `--quick` to the dashboard so it reads "Quick run, partial coverage".
5. Create a task list: one task per source, then extract and score, calibrate, dashboard, verify.

## The run

Use `<date>` for today and `R=search/runs/<date>`.

1. **Queries.** `queries --pending` prints the LinkedIn general queries, the per-company queries (tiers in `companies.dedicated_query_tiers`, batched) and the Indeed/Glassdoor/Dice searches. With `staging.enabled`, `queries --plan` shows the day-by-day plan and `queries --mark B2 --status DONE` records progress.
2. **Fetch.** Run each query through its connector (`references/sources.md` has actor inputs and known yields). Confirm an actor's input schema before the first call. Save every source's rows as a JSON list in `search/raw/<date>/<source>_<label>.json`, keeping the actor's field names and adding `"_source"`. Large datasets go to files; never read a full dataset into the conversation; count rows from the dataset, not the run summary.
3. **Sanity-check each source.** If every row falls outside the window, or ids are sequential or placeholder-like, or only link-shortener URLs appear, treat it as low-confidence: pass it through the filters but name it under `--unavailable` and in the notes. Mock or sample data is never used.
4. **Extract.** `extract --raw search/raw/<date> --out $R --date <date>` merges sources (LinkedIn over Indeed over the rest), applies the window, excluded companies, staffing and consulting patterns, title exclusions, the pay hard floor and the location rule. It writes `keep.json` and `dropped.json`. Silent exclusions never appear anywhere.
5. **Score.** `score $R/keep.json --date <date>` writes `scored.json` with score, buckets and the scope gate. Read `references/scoring.md` for what the arithmetic does and does not know.
6. **Calibrate.** If the command warns of saturation, or for the top roles in any case, read the descriptions of up to the budget in `references/scoring.md` (8 in a full run, 3 in a quick run), in the order given there. A keyword in a title is a trap until the description confirms the work. Record each change in `$R/adjustments.json` and run `adjust $R/scored.json $R/adjustments.json`. Every adjustment needs a `reason`; one that matches nothing is reported, so fix it.
7. **Liveness.** `liveness $R/scored.json --date <date>` drops postings that say closed or filled or whose apply-by date has passed. "Open" means the posting appeared in this run's own search results plus those text checks; job pages are not fetched. `liveness --held` lists held roles and which batches to re-run.
8. **Memory.** `seen annotate $R/scored_live.json`.
9. **Dashboard.** `dashboard $R/scored_live.json --dropped $R/dropped.json $R/dropped_live.json --date <date> --sources <sources that returned rows> [--unavailable <sources>] [--quick] [--notes "<scoring notes and adjustments>"]`. Add `--csv` only if the user wants a spreadsheet file or `outputs.csv` is on. It prints the run number.
10. `seen ingest $R/scored_live.json --run <N> --date <date> --filtered $R/dropped.json`, then `seen report --run <N>`.
11. `gaps ingest $R/scored_live.json --run <N>` if the user keeps the skill-gap report.

The dashboard has three tabs: Results, Filtered out and Applications (a read-only view of the tracker). Roles already in the tracker stay in Results with their status; do not hide a role because a package exists. A possible repeat of an earlier application (same company, similar title, closed or declined outcome) is shown, not hidden: tell the user which tracker entry it resembles and let `tailor-application` run the duplicate check.

## Verify before presenting

If a headless browser is available, open the saved HTML, confirm there are no page errors, the stat cards equal the list lengths, and each NEW badge equals the date test, and look at a screenshot. If no browser is available, say so and ask the user to open the file; do not call it verified.

## Summary to the user

```
Run #N (full | quick): X results, Y filtered, Z already in your tracker.
New since last run: company, title, salary, posted.
Priority (Strongest Fit, not yet applied): numbered list with match %.
  If none reached Strongest, say so and name the top Strong or Stretch roles.
Possible repeats of earlier applications: list with the tracker entry.
Sources this run: ...   Unavailable or low-confidence: ...
Descriptions read: N of M. Adjustments recorded: list with reasons.
Held roles needing a re-run: batches.
```

## Rules

1. Only listings returned by a real source; never invent a job, company or source.
2. Scores are a keyword heuristic, not a forecast; say so. Honest scoring beats a flattering list; a thin result set is a valid outcome.
3. Excluded companies are handled by the config; never add them back.
4. Applicant counts of 0 mean unknown.
5. A status in the tracker changes only when the candidate confirms it (`tracker update --confirmed`).
6. The candidate confirms a posting is open before applying; say that in the summary.
7. Scraping job sites is subject to each site's terms. The candidate is responsible for how they run the actors.
