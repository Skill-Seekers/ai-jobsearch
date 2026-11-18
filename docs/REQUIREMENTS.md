# Requirements

Two parts: what the suite must do (so you can check it), and what you must have to use it.

## A. What you need

| Need | Detail | If missing |
|---|---|---|
| Python 3.8 or newer | The `jobsearch` command line uses only the standard library. Run on 3.10 and 3.13; written for 3.8+. | Skills that call a tool report it and stop; nothing is simulated |
| Claude with Cowork or Claude Code | Runs the skills (`SKILL.md` files) | You can still run the tools by hand (`docs/CLI.md`) but the guided flows need Claude |
| A connected workspace folder | Where your config, resume, tracker and search results live | `setup-workspace` asks you to connect one first |
| Your resume (`.docx` preferred) and a metrics worksheet | The only sources of facts and numbers. `.md` works for everything except the ATS check | Tailoring and review ask for them |
| Job sources you connect yourself | Apify actors (LinkedIn, Glassdoor, Dice) and/or the Indeed connector | `job-search` stops and says what to connect; it never uses guesses or sample data |
| A browser | To open the HTML dashboard | |
| Optional: LibreOffice and `pdfinfo` | PDF export and page counts | Page count is reported as "not measured" |
| Optional: a Word skill/tool | `.docx` thank-you notes and cover letters | Saved as `.md` instead, and the skill says so |

Not required: a spreadsheet library, an account with this project, a database, network access for the tools themselves.

## B. Functional requirements

Each is testable. "Test" names where it is checked (`tests/` unless noted).

| ID | Requirement | Test |
|---|---|---|
| F1 | One JSON config per candidate drives all behaviour; no company, title or weight is hard-coded in the tools | `test_config` |
| F2 | The config is validated: required sections, regexes compile, paths stay inside the workspace, bucket thresholds descend, no wanted company is also excluded, at least one source enabled | `test_config` |
| F3 | Raw rows from several sources are merged and de-duplicated; the higher-priority source wins; a posting seen on two boards is one row | `test_pipeline` |
| F4 | Roles are dropped, with a reason, for: excluded company, staffing or consulting pattern, title exclusion (whole-word), pay maximum below the hard floor, outside the area and not remote, outside the date window. Companies marked silent leave no trace | `test_pipeline` |
| F5 | Scores are deterministic and capped; buckets follow the thresholds; a scope-gated role cannot rank above Stretch / Watch | `test_pipeline` |
| F6 | Manual score changes are recorded with a mandatory reason; an adjustment that matches nothing is reported | `test_pipeline` |
| F7 | Postings that say closed or filled, or whose apply-by date has passed, leave the results with a stated reason | `test_pipeline` |
| F8 | Every posting seen is remembered across runs (new, seen before, reposts, held) | `test_state` |
| F9 | The dashboard is one self-contained HTML file with Results, Filtered out and Applications tabs; the NEW badge is derived from the date in code; page text cannot break out of the script block | `test_state` |
| F10 | A CSV report is available on request, off by default, and formula-safe | `test_state` |
| F11 | The tracker matches a posting to prior applications by posting id, then by company plus at least two distinctive title words; a repeat-requisition check compares ids and text similarity | `test_state` |
| F12 | A tracker status changes only with an explicit `--confirmed`; a new entry starts as drafted and not applied | `test_state` |
| F13 | The ATS check reports parse-safety problems and JD keyword gaps, never inserts text, and blocks terms the candidate has ruled out claiming | `test_resume_tools` |
| F14 | The skill-gap report marks each requirement Claimed, Decided no, or Gap from the candidate's own files | `test_resume_tools` |
| F15 | Every skill states its approval gates and guardrails; none writes a resume or letter before the user says go | review (see `docs/BUILD_PROCESS.md`) |
| F16 | Role-specific wording lives in config sections and `references/role-*.md` files, so another role replaces data and text, not logic | review |

## C. Non-functional requirements

| ID | Requirement |
|---|---|
| N1 | Standard library only; Python 3.8+ |
| N2 | Same inputs give byte-identical scores and the same dashboard data |
| N3 | No network access from the tools; no credentials stored anywhere |
| N4 | No personal data in the repo; verified by `tools/privacy_scan.py` before every release (`docs/BUILD_PROCESS.md`) |
| N5 | A missing optional input degrades gracefully with a stated reason (for example "not measured"); it never fabricates |
| N6 | Every command exits 0 (done), 1 (finished, but something needs action) or 2 (could not run) |
