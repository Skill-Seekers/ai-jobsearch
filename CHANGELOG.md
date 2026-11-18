# Changelog

## 0.2.0 (unreleased)

First public version, generalised from a personal TPM job-search setup.

- One Python package and one command line (`python -m jobsearch`), standard library only: `check`, `queries`, `extract`, `score`, `adjust`, `liveness`, `seen`, `dashboard`, `tracker`, `ats`, `gaps`.
- One JSON config per candidate (`jobsearch.config.json`). Tiers drive both scoring and per-company LinkedIn queries.
- Seven skills: `setup-workspace`, `job-search`, `tailor-application` (merges apply-to-job and tailor-resume), `resume-review` (merges resume-audit and resume-update), `profile-audit`, `interview-prep`, `interview-thank-you`.
- Role-specific text isolated in config sections and `references/role-*.md` files; TPM is the worked example, with a data science engineer example for adapting.
- HTML dashboard on every run with an Applications tab (replaces the separate roster files); optional zero-dependency CSV (replaces XLSX).
- Tracker: one file, no mirror; status changes need `--confirmed`.
- Fictional sample workspace, a one-command demo, 52 tests.
- Privacy gate: `tools/privacy_scan.py` with a private denylist kept outside the repo.
- Role-specific values moved out of the code and into `jobsearch.config.json`: `ats_generic_terms` (ATS check), `tracker_generic_words` (tracker matching) and `scoring.points` (score adjustments). Defaults reproduce the previous behaviour; the shipped example still uses the TPM values.
- Job-description intake lists the accepted inputs explicitly (URL, pasted text, `.txt`/`.md` file, `.docx`/`.pdf` converted to text) and reads folder locations from `paths` instead of fixed folder names.
- Fixes found while porting: title exclusions now match whole words (a "software engineer" exclusion no longer drops "Software Engineering Program Manager"); Indeed posting ids survive link clean-up; rebuilding a day's dashboard keeps its run number.
