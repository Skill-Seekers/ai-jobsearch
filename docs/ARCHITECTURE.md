# Architecture

Status: implemented in v0.2.0 (tools and tests). The skills are written but not yet exercised in a live session; see `LIMITS.md`.

## Principles

1. **One config, one tracker.** A candidate has a single `jobsearch.config.json` and a single `applied_tracking.json`. Skills and tools read them; nobody edits the skills to change behaviour. See `CONFIG.md`.
2. **Scripts do arithmetic, skills do judgment.** Scoring, de-duplication, filtering, liveness checks, tracker matching, ATS checks and report building are deterministic, so they live in tested scripts. A `SKILL.md` holds the steps that need judgment and the approval gates.
3. **Standard library only.** Python 3.8+. No installs. Every output (dashboard, CSV) works without extra libraries.
4. **Nothing connects itself.** The suite never logs in to a job site or creates an account. The candidate connects sources beforehand; an unavailable source is skipped and noted, and sample data is never substituted.
5. **A human approves every write and every claim.** Numbers come only from the candidate's metrics worksheet or resume. A gap between a posting and the resume is flagged, never papered over. The tracker changes status only when the candidate confirms.

## The workspace (the candidate's own folder, kept outside this repo)

```
my-workspace/
  jobsearch.config.json          one config
  resume/master/                 master resume (.docx or .md)
  resume/metrics-worksheet.md    the only source of numbers
  resume/job_descriptions/       saved JDs, one .txt per posting
  resume/tailored/<Company-Role>/  resume, cover letter, tailoring notes, ats-check
  tracking/applied_tracking.json one tracker
  search/                        dashboards, optional CSV, run state (seen_jobs.json, staged_run.json)
  interview/  profile/           prep notes, LinkedIn drafts
```

`examples/sample-workspace/` is a complete fictional workspace (candidate "Alex Rivera") used by the docs, the demo and the tests.

## Data flow of one search run

```
config ──► queries ──► [connectors: LinkedIn, Indeed, Glassdoor, ...] ──► raw rows (search/raw/<date>/)
raw rows ──► extract  (merge, de-duplicate, date window, company/title/pay/location exclusions) ──► keep.json, dropped.json
         ──► score    (tier, domain, level, location, pay; then the scope gate; buckets)         ──► scored.json
         ──► adjust   (manual changes, each with a reason, after the skill reads top descriptions)
         ──► liveness (drop postings that say closed or are past an apply-by date)              ──► scored_live.json
         ──► seen     (new vs seen before, reposts, held roles; remembered across runs)
         ──► dashboard (HTML always, CSV if enabled); the tracker marks roles already applied to
```

The skill pulls rows from the connectors; every other box is a script, so the same inputs always give the same dashboard.

## Skills (7) and the tools they call

| Skill | Does | Calls |
|---|---|---|
| `setup-workspace` | Interview, then writes the config, folders and an empty tracker (Step 0; every other skill stops and runs this if the config is missing) | `check` |
| `job-search` | Runs the sources, then the flow above; presents the top roles and what changed since last run | `check`, `queries`, `extract`, `score`, `adjust`, `liveness`, `seen`, `dashboard`, `gaps ingest` |
| `tailor-application` | From a posting URL or a saved JD: duplicate and closed-req check, signal analysis, tailoring plan, edit gate, optional cover letter, final approval, files, ATS check, tracker entry as *drafted* | `tracker dupes`, `ats`, `tracker add` |
| `resume-review` | Audit mode (recruiter-style findings) and update mode (six improvement prompts, confirmed edits, new version each time) | `ats`, `gaps` |
| `profile-audit` | LinkedIn headline, About, experience, keywords, elevator pitch | none |
| `interview-prep` | Recruiter pre-screen, STAR stories, leadership principles, technical scenarios, mock | none |
| `interview-thank-you` | One short, specific note per interviewer, saved as .docx for the candidate to send | none |

Merged from the original nine: `apply-to-job` and `tailor-resume` became `tailor-application` (same loop; only how the posting arrives differs), and `resume-audit` and `resume-update` became `resume-review`.

## Tools: one CLI

`python -m jobsearch <command>`; every command has `--help`; exit 0 = done, 1 = finished but something needs action, 2 = could not run. Full reference: `CLI.md`. A missing optional input never aborts a run.

| Command | Purpose |
|---|---|
| `check` | Validate the config (types, regexes, paths) and print a summary |
| `queries [--source S]` | Print the search queries or URLs to run, in batches |
| `extract --raw DIR --out DIR [--date D]` | Merge and de-duplicate rows; apply the date window and exclusions; write kept and dropped rows |
| `liveness FILE --date D` | Drop postings whose text says closed or past a deadline; list held roles that were not seen again |
| `score FILE [--date D]` |
| `adjust FILE ADJ.json` | Apply manual score changes; each needs a reason | Score, bucket, apply the scope gate |
| `seen ingest|report|hold|stats` | Cross-run memory of every posting: new, seen before, reposts, held |
| `dashboard FILE [--csv]` | Build the HTML dashboard (and the CSV when enabled); includes an Applications tab drawn from the tracker |
| `tracker match|dupes|add|update|report` | Find the prior application a posting resembles; check for a repeat requisition; add a *drafted* entry; record a status the candidate confirmed (`--confirmed`) |
| `ats RESUME.docx JD.txt` | Parse-safety check and keyword gaps; flags terms the candidate has ruled out claiming |
| `gaps` | What saved postings ask for that the master resume does not claim |

## Tracker

One JSON file, one entry per posting (a sibling req is its own entry). Core fields: `id`, `company`, `title`, `req_id`, `source_job_id`, `jd_file`, `folder`, `title_keywords`, `status` (drafted, applied, screen, interview, offer, declined, closed, passed), `applied` (true only on the candidate's confirmation), `applied_date`, `tailored_date`, `outcome`, `notes`. A field that is empty means *not recorded*, never *did not happen*. There is no mirror copy.

## Changes from the original personal setup

| Original | Here | Why |
|---|---|---|
| Separate roster HTML and XLSX | An *Applications* tab in the dashboard, built from the tracker | One output to keep correct; the two files had drifted apart |
| XLSX per run | Optional CSV | No libraries to install |
| Company lists and weights written into the skill text | In the config | Another candidate edits data, not skills |
| Seven scripts | One package, one CLI | Easier to learn and test |
| Tracker mirror | Removed | It existed only because the old skills were read-only |
| Staged scrape plan | Optional (`staging.enabled`) | Only needed under a usage limit |
| Slash-command files that duplicated skills | Dropped | Skills are the only interface |

## Decisions confirmed

1. The roster is an *Applications* tab in the dashboard, not a separate file.
2. Tiers drive both scoring and which companies get dedicated LinkedIn queries; batch labels are derived.
3. TPM is the worked example only. A different role replaces the config sections *and* the role text
   in each skill's `references/role-*.md` file (see `CONFIG.md`, "Adapting to a different role"). The
   engine, approval gates and guardrails do not change.
