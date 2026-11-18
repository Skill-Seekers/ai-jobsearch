# ai-jobsearch

A guarded, AI-assisted job-search workflow for [Claude](https://claude.com) (Cowork and Claude Code). It finds roles, scores them with a transparent rule set, tailors your resume to each posting with an approval at every step, tracks what you applied to, and helps you prepare for interviews.

It was built by one Technical Program Manager (TPM) for their own search and then generalised. **TPM is the worked example, not a requirement.** If you are a data science engineer, a product manager or anything else, you replace the role-specific sections of one config file and five short text files. See [Adapting to another role](docs/ADAPTING.md).

> **Status: v0.2.0, early.** The command-line tools are tested (52 automated tests on fictional data). CI runs them on Python 3.8 through 3.13; the local run was on Python 3.10. The skills are mechanically checked against the tools (commands, flags, file references) but have **not yet been run in a live Cowork or Claude Code session**, and the plugin has not been installed. Read [Limits](docs/LIMITS.md) before you rely on it.

## What you get

| Skill | What it does |
|---|---|
| `setup-workspace` | Interviews you and writes `jobsearch.config.json`, the folders and an empty tracker. Run first. |
| `job-search` | Runs your connected sources, filters, scores, drops closed postings, remembers what earlier runs saw, builds an HTML dashboard (CSV optional). |
| `tailor-application` | From a posting URL or saved JD: repeat-application check, signal analysis, tailoring plan, edit-by-edit approval, optional cover letter, ATS check, tracker entry. |
| `resume-review` | Recruiter-style audit, ATS formatting check, skill-gap report, and six guarded editing prompts. |
| `profile-audit` | LinkedIn headline, About, experience, keywords, elevator pitch. |
| `interview-prep` | STAR practice, leadership principles, role scenarios, mock interview, recruiter pre-screen. |
| `interview-thank-you` | A short, specific note per interviewer. |

Behind the skills is one command line, `python -m jobsearch`, written in the Python standard library only (nothing to install). It does the arithmetic (de-duplication, scoring, filtering, tracker matching, the dashboard) so the same inputs always give the same output; the skills handle judgement and approvals.

## How it behaves

- **Nothing is invented.** Only postings returned by a real source are listed. Resume numbers come only from your metrics worksheet or master resume. A gap between a posting and your resume is flagged, never papered over.
- **You approve every write.** Nothing is written to a resume or cover letter until you say go. A tracker status changes only when you confirm it.
- **Your data stays yours.** The suite holds no credentials and connects to no job site itself; you connect your own sources. Your resume, tracker and search results live in your own workspace folder, outside this repo.
- **Scores are a heuristic, not a forecast.** The scorer is keyword arithmetic you can read and edit. It saturates near its cap, so the skill reads the top descriptions and records any change with a reason.
- **"ATS friendly" means formatting guidance only** (plain headings, no text boxes, readable text layer). Nobody can promise how an employer's ATS ranks a resume.

## Quick start

1. **Try it with no setup** (no accounts, no network). From a clone of this repo:

   ```
   python examples/run_demo.py
   ```

   It builds a fictional workspace (candidate "Alex Rivera"), runs the whole pipeline and prints the path of a dashboard to open in a browser. See [the demo walkthrough](docs/DEMO.md).

2. **Use it for real.** Follow [INSTRUCTIONS](docs/INSTRUCTIONS.md): install the plugin, connect your sources, run `setup-workspace`, then `job-search`.

Requirements in one line: Python 3.8+ for the tools; a Claude plan with Cowork or Claude Code for the skills; your own connectors for live job data (Apify actors and/or the Indeed connector). Details in [REQUIREMENTS](docs/REQUIREMENTS.md).

## Documentation

| Read | For |
|---|---|
| [INSTRUCTIONS](docs/INSTRUCTIONS.md) | Install, first run, the daily flow, troubleshooting |
| [REQUIREMENTS](docs/REQUIREMENTS.md) | What the suite must do and what you must have |
| [ASSUMPTIONS](docs/ASSUMPTIONS.md) | What it takes for granted (read before trusting a score) |
| [SCOPE](docs/SCOPE.md) | What is in scope and what is not |
| [ADAPTING](docs/ADAPTING.md) | Replacing the TPM example with your role |
| [IMPORT-TO-OTHER-AI](docs/IMPORT-TO-OTHER-AI.md) | Giving the repo to ChatGPT or Gemini to build a similar tool |
| [CONFIG](docs/CONFIG.md) | Every key in `jobsearch.config.json` |
| [CLI](docs/CLI.md) | Every command, with exit codes |
| [DATA_SCHEMAS](docs/DATA_SCHEMAS.md) | The file formats the tools read and write |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | How the pieces fit |
| [LIMITS](docs/LIMITS.md) | What it cannot do and what is untested |
| [BUILD_PROCESS](docs/BUILD_PROCESS.md) | How this repo is built and how personal data is kept out of it |
| [CONTRIBUTING](CONTRIBUTING.md) | Running the tests and the privacy scan |

## Responsibility

Automated collection from job sites may be restricted by their terms of service. You decide which sources to connect and you are responsible for how you use them; this project ships no scrapers and no credentials. Resume and cover-letter text produced with AI must be checked by you before you send it, and you remain responsible for every claim in it. This is not career, legal or financial advice.

## License

[MIT](LICENSE). The example data (people, employers, postings, numbers) is entirely fictional; any resemblance to a real person or company is accidental.
