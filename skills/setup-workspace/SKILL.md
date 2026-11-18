---
name: setup-workspace
description: Sets up the job-search workspace for a new user — creates the folder layout, writes jobsearch.config.json through a short interview (including the role-specific sections), and initializes the application tracker. Use when the user says "set up my job search", "first-time setup", "configure ai-jobsearch", or when another ai-jobsearch skill reports that jobsearch.config.json is missing.
---

# Setup Workspace

Create the folders and the one config file that every other skill and the `jobsearch` command line read. Run this once per candidate; every other skill stops and sends the user here if `jobsearch.config.json` is missing.

**The shipped example is a Technical Program Manager. It is an example, not a requirement.** The role-specific parts of the config (target titles, scoring keywords, scope gate, skill vocabulary, title exclusions) must be replaced for another role. Read `references/role-adaptation.md` and do that during the interview.

## Running the tools

`python3 <plugin root>/jobsearch <command>` from inside the workspace folder (the config is found by walking up from the current folder). `<plugin root>` is `${CLAUDE_PLUGIN_ROOT}` when set, otherwise the folder two levels above this skill's base directory (the one that holds `skills/` and `jobsearch/`). Commands are listed in `docs/CLI.md`.

## Steps

1. Confirm the workspace folder is connected. If not, ask the user to connect one first.
2. If `jobsearch.config.json` already exists, run `check`, show the summary, and ask what to change. Never rebuild an existing config.
3. Read `assets/config.template.json` (this skill's folder). It is the working TPM example with fictional names.
4. Interview in short rounds with AskUserQuestion where choices are discrete. Skip anything already known:
   - **Round 1, identity:** name, file prefix for output files, sign-off name, email (phone and LinkedIn optional).
   - **Round 2, role:** the target role family. If it is not Technical Program Manager, follow `references/role-adaptation.md` to rewrite `targets`, `title_exclusions`, `scoring.domain_families`, `scoring.negative_families`, `scoring.title_match`, `scope_gate`, `skill_vocabulary`, `ats_generic_terms`, `tracker_generic_words`, `scoring.points` and the `sources` search terms. Show each rewritten section to the user before writing it.
   - **Round 3, where and how much:** preferred locations (and the `scoring.home_locations` words that match them), work modes, compensation floor, seniority words.
   - **Round 4, companies:** tiers 1 to 3 with aliases, companies to avoid (and whether they are hidden `silent` or shown in the Filtered tab), former employers to flag, staffing patterns to keep.
   - **Round 5, guardrails:** "What must the resume and cover letters never claim?" Write each answer into `do_not_claim` (term, aliases, reason) and `claims_limits`. This is the guardrail against overstating; do not skip it.
5. Write `jobsearch.config.json` at the workspace root. Leave an unknown value empty; never guess. Replace every fictional name from the example (Alex Rivera, Contoso, Fabrikam and the rest) with the user's values or remove it.
6. Run `check`. Fix every ERROR with the user; show warnings (for example a master resume path that does not exist yet).
7. Create the folders named under `paths` (default: `resume/master`, `resume/job_descriptions`, `resume/tailored`, `tracking`, `search`, `interview`, `profile`) and `tracking/applied_tracking.json` containing `{"schema_version": "1.2", "applications": []}`. If the user has a tracker in this schema, copy it in (never edit the original) and tell them an entry without a `source_job_id` can only match by keywords.
8. Ask the user to place the master resume (`.docx`; `.md` works for everything except the ATS check) and the metrics worksheet in their folders. If they paste the resume instead, save it as `resume/master/<prefix>_v1.0.md`.
9. Read the config back and ask for corrections. Finish with one line: run `job-search`, or `tailor-application` with a posting URL.

## Rules

- Never invent a value. Missing is better than guessed.
- Do not copy personal data from anywhere except what the user states in this session or in files they tell you to use; say where each non-obvious value came from.
- Paths in the config stay inside the workspace (no absolute paths, no `..`); `check` enforces it.
- The suite connects to no job source. Tell the user which connectors the search needs (see `docs/INSTRUCTIONS.md`, Prerequisites) and that setting them up is their step.
