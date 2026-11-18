# Instructions

From nothing to a first real search. About 30 minutes, most of it connecting your sources.

## 0. Try it first (5 minutes, no accounts)

```
python examples/run_demo.py
```

Open the dashboard it prints. Everything in it is fictional. [DEMO](DEMO.md) explains each step.

## 1. Prerequisites (your side; the suite does none of this)

1. **Claude with Cowork or Claude Code**, and a workspace folder connected to the session. Keep this folder separate from this repo: it will hold your resume, tracker and search results.
2. **Python 3.8 or newer** available to the session (`python3 --version`).
3. **Sources.** For live search connect at least one:
   - LinkedIn, Glassdoor and Dice through [Apify](https://apify.com) actors (the Apify connector in your Claude session). Free plans limit concurrent runs; see `skills/job-search/references/sources.md` for tested inputs.
   - Indeed through its Claude connector.
   Without a source, `job-search` stops and says what to connect. You can still use every other skill.
4. **Your documents.** A master resume (`.docx` preferred) and a **metrics worksheet**: the only source of numbers the suite will ever put on a resume. One line per claim: the employer, the claim, the number, and where you can prove it.
5. Optional: LibreOffice and `pdfinfo` for PDF export and page counts; a Word skill for `.docx` letters.

## 2. Install

**Cowork:** build the package and add it as a plugin.

```
python tools/build_plugin.py          # writes dist/ai-jobsearch-0.2.0.plugin
```

Install the `.plugin` file through the plugins screen of the desktop app, or download it from the repository's Releases page when a release exists.

**Claude Code:** add this repository as a plugin marketplace and install `ai-jobsearch` from it (see Claude Code's plugin documentation for the current commands; the manifest is `.claude-plugin/marketplace.json`). Or copy the `skills/` folders into your skills directory and keep the repo cloned so the skills can find `jobsearch/`.

The skills call the tools as `python3 <plugin root>/jobsearch <command>` where `<plugin root>` is the folder that contains `skills/`. If `${CLAUDE_PLUGIN_ROOT}` is set they use it; otherwise they find the folder from the skill's own location. If a skill cannot find the tools it says so and stops.

> The plugin has not yet been installed or run in a live session; see [LIMITS](LIMITS.md). If an install or a skill fails, copy the exact error into an issue.

## 3. First run

1. Say **"set up my job search"**. `setup-workspace` interviews you and writes `jobsearch.config.json` and the folders. **If your role is not Technical Program Manager, tell it so in round 2**: it will rewrite the role-specific sections with you (see [ADAPTING](ADAPTING.md)). Replace the five `references/role-*.md` files afterwards.
2. Put your master resume and metrics worksheet where the config says (`resume/master/`, `resume/metrics-worksheet.md`).
3. `python3 <plugin root>/jobsearch check` (or ask Claude to). Fix every ERROR; read the warnings.
4. Say **"run a quick job search"** to test your sources (two sources, small limits). Then **"run the job search"** for a full run.

## 4. The flow after that

| You want to | Say | What happens |
|---|---|---|
| Find roles | "run the job search" | Runs connected sources, filters, scores, reads the top descriptions, builds `search/job_search_<date>.html` |
| Apply to one | "apply to this job: <URL>" | Saves the JD, checks for a repeat, shows a tailoring plan, edits one row at a time, you type go, files are written, ATS check, tracker entry as drafted |
| Say you applied | "I submitted the Tailspin application" | The tracker records it, with the date, after you confirm |
| Improve the master resume | "audit my resume" / "update my resume" | Audit, ATS check, six guarded prompts, new version saved |
| See skill gaps | "what skills am I missing" | `skill_gap_report.html` |
| Fix LinkedIn | "rewrite my headline" | Eight prompts, approval before saving |
| Prepare | "I have an interview at <company>" | STAR, scenarios, mock, recruiter pre-screen |
| Say thanks | "write a thank-you note to <name>" | One note per interviewer, saved |

Read the dashboard's **Applications** tab for your tracker; **Filtered out** to check nothing good was dropped.

## 5. Everyday habits that keep results honest

- Confirm a posting is open on the employer's site before you apply.
- Open the top results' descriptions yourself. The score is a first sort.
- Keep the metrics worksheet current; it is the only place numbers come from.
- Add a company alias when a name is not recognised; add a `do_not_claim` line when you decide not to claim something.
- Tell the tracker when you submit, and when you hear back.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR No jobsearch.config.json found` | Not run from the workspace | `cd` into it or pass `--config` before the command |
| `check` says a path "must stay inside the workspace" | Absolute path or `..` in `paths` | Use a relative path |
| Few results | A narrow window, a strict location rule, or one source | Read the Filtered tab; widen `posted_within_days`; check `--unavailable` sources |
| Everything scores 95+ | The scorer saturates | Expected; the skill calibrates; or edit `domain_cap` and families |
| Wrong roles rise to the top | The role sections are still the TPM example | [ADAPTING](ADAPTING.md) |
| A good role is in Filtered | Title exclusion, location rule or staffing pattern | The reason is shown; adjust the config |
| `tracker update` refused | No `--confirmed` | Pass it only after you confirmed |
| Excel shows odd characters in the CSV | Older Excel ignoring the byte-order mark | Import with UTF-8, or use the dashboard |
| Dashboard shows a link as `#` | The link was not http(s) | The source returned a malformed link |
| The ATS check says "not found" for a heading | Non-standard heading or text inside a text box or table | Use plain headings in the body |
