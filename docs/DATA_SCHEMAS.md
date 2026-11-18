# Data schemas

All files are UTF-8 JSON unless noted. Dates are `YYYY-MM-DD`. A field that is empty means *not recorded*, not *did not happen*.

## Raw rows (input to `extract`)

One file per query or source in `search/raw/<date>/`, each a JSON list (or `{"items": [...]}`) of rows. Field names are the LinkedIn actor's; these aliases are accepted:

| Field | Aliases | Notes |
|---|---|---|
| `companyName` | `company` | required |
| `title` | | required |
| `location` | | |
| `postedAt` | `posted`, `datePosted`, `date` | first 10 characters must be `YYYY-MM-DD`, else the date is treated as unknown and the row is flagged |
| `applicantsCount` | `applicants` | digits only are read; "200+" becomes 200; unknown becomes 0 |
| `salary` | | text such as `$150,000 - $210,000` or `$150K-$210K` |
| `employmentType`, `seniorityLevel` | `employment`, `seniority` | |
| `link` | `url` | the query string is dropped, except Indeed's `jk=` id |
| `descriptionText` | `description`, `desc` | first 4,500 characters kept |
| `_source` | `source` | LinkedIn, Indeed, Glassdoor, Dice, Google Jobs; guessed from the link if absent |

## keep.json / scored.json / scored_live.json

`extract` writes `keep.json`: normalised rows with `source, company, title, location, posted, applicants, salary, employment, seniority, link, desc` and an optional `note`. `score` adds `score` (0 to `base_cap`), `why` (signals that fired), `tier`, `scope` (`in` or `out`) and `scope_reason`, `bucket` (`Strongest Fit`, `Strong Fit`, `Stretch / Watch`, `Filtered`), `workMode`. `adjust` appends to `adjustments`: `{old, new, reason}`. `liveness` adds `live`, `live_note`, `live_checked`. `seen annotate` adds `is_new`, `times_seen`, `first_seen`, and `repost_of` when it applies.

## dropped.json / dropped_live.json

Rows that left the list: the row fields plus `cat` (`COMPANY`, `TITLE`, `PAY`, `LOCATION`, `CLOSED`), `reasonType` (`excl` excluded company, `staff` staffing or consulting, `wrong` does not fit) and a human-readable `reason`. Companies marked `visibility: silent` are never written.

## adjustments.json

```json
[{"company": "Example Co", "title_contains": "Bring-up", "delta": -12, "reason": "Description requires 5+ years of RTL design."},
 {"link_contains": "0000000101", "set": 70, "bucket": "Strong Fit", "reason": "..."}]
```

Match by `link_contains`, or by `company` plus `title_contains`. Use `delta` or `set`. `reason` is mandatory.

## Tracker: `tracking/applied_tracking.json`

```json
{"schema_version": "1.2", "applications": [{
  "id": "company-role-slug", "company": "Example Co", "title": "Exact title", "req_id": null, "source_job_id": "0000000101",
  "jd_file": "resume/job_descriptions/...", "folder": "Example-Co-Role", "title_keywords": ["controller", "firmware"],
  "status": "drafted", "applied": false, "applied_date": null, "tailored_date": "2026-10-20",
  "outcome": null, "notes": ""}]}
```

`status`: drafted, applied, screen, interview, offer, declined, closed, passed. `applied` is true only on your confirmation. `company: null` is allowed for an anonymous posting and never auto-matches. Matching: `source_job_id` found in the posting link first (any status); otherwise normalised company equal and at least two distinctive `title_keywords` in the title, on entries with `applied: true`. Generic words (program manager, senior, staff, engineer and the like) never count.

## Seen store: `search/state/seen_jobs.json`

`{"schema_version", "updated", "jobs": {key: {company, title, location, posted, link, first_seen, last_seen, first_run, last_run, runs, times_seen, best_score, last_score, state, filter_reason, repost_of, tracker_id, held_since}}, "runs": {"1": {"date", "rows_ingested"}}}`. Keys are `li:<id>`, `indeed:<jk>` or `x:<hash>`. `state` is `seen`, `filtered`, `listed`, `held` or `applied`. `repost_of` names an earlier posting with the same company and title when exactly one such role appears in a run; `tracker_id` links a posting to your tracker entry.

## Staged-run state: `search/state/staged_run.json`

`{"batches": {"B1": {"status": "DONE", "date": "2026-10-26"}}}`.

## Skill-gap data: `search/state/skill_gap_data.json`

`{"postings": {key: {"run", "score", "terms": [skill ids], "min_years"}}}`. Only matched skill ids and a years-asked number are stored, never posting text.

## Dashboard data

The HTML embeds one JSON object, `DATA`: `run, date, new_days, filter_label, sources_label, footer, notes, results[], filtered[], applications[]`. Result rows: `num, match, bucket, source, company, title, workMode, employment, applicants, location, posted, salary, link, note, is_new, why, applied_id, applied_status`.

## CSV (optional)

UTF-8 with a byte-order mark. Columns: Rank, Match, Bucket, Company, Title, Location, Work mode, Posted, Salary, Source, Recently posted, In tracker, Note, Link. A cell that starts with `=`, `+`, `-`, `@`, tab or carriage return gets a leading apostrophe so a scraped title can never run as a formula.
