# Limits and what is untested

Read this before you rely on the suite.

## Untested

| Item | Status |
|---|---|
| The skills (`SKILL.md` files) in a live Cowork session | Written and reviewed; the plugin has **not been installed and run end to end**. The tools they call are tested. |
| Claude Code | Same skill format, **not tried**. Marketplace and install commands may need adjusting. |
| Live connectors (Apify, Indeed) | Not exercised by the tests, which use fictional rows. Actors and their fields change; confirm schemas before use. |
| Python versions | Run on Python 3.10 and 3.13. Written to avoid syntax newer than 3.8; `.github/workflows/tests.yml` runs 3.8 to 3.13 on GitHub, but that workflow has not run yet. |
| Windows paths with spaces or non-ASCII names | Not specially tested |
| Very large result sets (thousands of rows) | Not tested for speed |

## What the scoring can and cannot do

- It is keyword arithmetic. It cannot read nuance, tell a real requirement from boilerplate, or know your preferences beyond the config.
- It saturates: several roles tie near the cap. Calibration by reading descriptions is a required part of the run, not an extra.
- Keyword lists favour English, and favour the field you configure.

## What "open" means

A role is treated as open if it appeared in this run's search results and its text does not say closed or filled and has no past apply-by date. The suite does not fetch job pages (many block it). A role can close an hour after you see it.

## What "ATS friendly" means

Formatting guidance: a readable text layer, plain headings, no text boxes or images carrying text, contact details in the body. Keyword coverage is a heuristic ranking of terms in the posting. Nobody outside an employer can predict how its ATS scores a resume, and this suite does not claim to.

## Data and privacy

- The tools write only inside your workspace. They hold no credentials and do no network calls.
- Job descriptions you save and the seen-jobs store may contain employer text and posting links. Keep your workspace private. The seen store and skill-gap data keep matched terms and titles, not full postings, but treat them as personal data.
- Resume, tracker and search results are in your workspace, never in this repo. `tools/privacy_scan.py` exists so a fork or release can be checked before publishing ([BUILD_PROCESS](BUILD_PROCESS.md)); it reduces the risk of leaking personal data, it does not remove it.

## Terms of service

Scraping or automated collection may breach a job site's terms. You choose the sources and are responsible for your use of them. This project ships no scrapers.

## Known gaps

- English only. USD salaries only.
- An apply-by date with no year ("Dec 20") is read in the run's own year; a December deadline seen in early January would be read as in the future.
- A salary range written in words or another currency is "not listed".
- Title exclusions match whole words; a title that merely contains an excluded word as a separate word is dropped (for example "Controller" in "Storage Controller Program Manager" if you list `controller`). Use longer phrases.
- Company aliases of four characters or fewer match whole words only; longer ones match as substrings, so a short brand inside a longer name needs care.
- No locking: do not run two searches into the same workspace at once.
- The dashboard's Applications tab is read-only; changes go through the tracker command.
