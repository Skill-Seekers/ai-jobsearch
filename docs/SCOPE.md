# Scope

## In scope

- **Finding roles** from sources you have connected: general title queries, per-company queries driven by your tiers, board searches, merged and de-duplicated.
- **Filtering and scoring**: exclusions, a date window, a pay and location rule, a transparent keyword score, a scope gate, manual calibration with recorded reasons, closed-posting checks, cross-run memory of what was seen.
- **Output**: an HTML dashboard on every run (Results, Filtered out, Applications), and an optional CSV report.
- **Applying, with you in control**: saving a job description, a repeat-application check, signal analysis, an edit-by-edit tailoring plan, an optional cover letter, an ATS formatting check with keyword gaps, a tracker entry that starts as drafted.
- **Tracking** your applications in one JSON file, with statuses you confirm.
- **Resume review** (audit, six editing prompts, skill-gap report) and **LinkedIn** profile audit and rewrite.
- **Interview preparation** (STAR, principles, role scenarios, mock, recruiter pre-screen) and **thank-you notes**.
- **Adapting to another role** by replacing config sections and five reference text files.

## Out of scope

| Not included | Why / what to do instead |
|---|---|
| Connecting, logging in to or scraping job sites | You connect sources yourself; the suite holds no credentials and ships no scrapers |
| Applying on your behalf: no form filling, no submitting, no sending email or messages | You submit; you tell the tracker when you did |
| Guaranteeing an ATS result or predicting a hiring decision | "ATS friendly" is formatting guidance only |
| Verifying that a posting is open | It can only check what a run saw plus text cues; confirm on the employer's site |
| Inventing experience, metrics, titles or certifications | Refused by design; gaps are flagged |
| Salary negotiation, offer comparison, legal or immigration advice | Not covered; not advice |
| Networking, referrals, outreach to recruiters | Outside the loop; `interview-thank-you` is the only message writer |
| Resume design or templates beyond plain, parser-safe formatting | Use your own template; the ATS check reads what you give it |
| Multi-user or hosted use, a database, a web server | One person, one folder |
| XLSX output | A zero-dependency CSV opens in any spreadsheet app |
| Windows/macOS/Linux installers, an auto-updater | Clone or download; run with Python |
| Languages other than English | Keyword lists and patterns assume English |
| Replacing your judgement | Every score and draft is a starting point |

## Boundary notes

- The tools never reach the network. Everything that does (connectors, fetching a posting URL, converting PDFs) is done by the skill with tools you have enabled, and each of those steps degrades with a stated reason when unavailable.
- Resume and cover-letter editing is in scope; formatting a final document with a Word or PDF tool depends on what your session has. Without one, the skill says "not measured" or saves markdown.
