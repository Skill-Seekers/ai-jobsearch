---
name: resume-review
description: Reviews and improves the master resume — a blunt recruiter-style audit, an ATS formatting check, a skill-gap report, and a guarded editing session with six named prompts that saves a new version only after approval. Use when the user says "audit my resume", "review my resume", "is my resume ATS friendly", "update my resume", "rewrite my resume", "improve my bullets", "what skills am I missing", or wants a gut-check before applying.
---

# Resume Review

Two modes in one skill: **audit** (read and report) and **update** (edit, with approval). The role-specific checklist is in `references/role-checklist.md` (the shipped example is a Technical Program Manager; replace it for another role, see `docs/ADAPTING.md`).

## Setup

Run tools with `python3 <plugin root>/jobsearch <command>` from inside the workspace (`<plugin root>` is `${CLAUDE_PLUGIN_ROOT}` when set, otherwise the folder two levels above this skill's base directory, the one that holds `skills/` and `jobsearch/`). Read `jobsearch.config.json` for the master resume path, metrics worksheet, target titles, `claims_limits`, `do_not_claim` and page limit. If the config is missing, run `setup-workspace`. State which resume version you loaded.

## Mode 1: audit

Audit as a senior recruiter screening hundreds of resumes a day for the target roles. Answer each point with specifics, naming bullets and sections so the user can find them:

- **First impression (10-second scan):** what is noticed first and the gut reaction.
- **Positioning:** is the target role obvious from the subhead and summary, or is the value proposition generic?
- **Impact:** which bullets state outcomes with a number and which are task lists; name the weak roles.
- **Structure and ATS:** skimmability, inconsistent formatting, columns, tables or text boxes a parser may drop, dates, page count. Run `ats <resume.docx> <a saved JD>` against a representative posting for the parse-safety part.
- **Top three rejection reasons:** each tied to a named bullet or section.

Keep it short and blunt; no encouragement filler. Then offer the next step: the six-prompt update below, or the skill-gap report.

## Mode 2: skill gaps (optional)

`gaps report` reads every saved JD and any strong-fit scrape terms you ingested, compares them with the master resume, and writes `search/skill_gap_report.html`. Status per requirement: **Claimed** (on the resume), **Decided no** (on `do_not_claim`), **Gap**. Counts are keyword matches ("mentioned", not "required"), and saved JDs lean toward the user's targets. Present the top gaps and ask which are real experience worth adding and which to leave; never add a skill the user does not have. Requires `skill_vocabulary` in the config (role-specific).

## Mode 3: update

A guarded session. Nothing is written until the user approves; a prior version is never overwritten.

1. Show the six prompts and ask which to run (one, several, all in order).
2. Run them one at a time. After each, show BEFORE and AFTER and ask: apply, skip, or modify.
3. Write only on explicit confirmation, as a new file with the version bumped (v1.0 to v1.1).
4. Re-open the file and assert every approved edit is present and nothing was removed by mistake. Run `ats` on it and report parse-safety and any do-not-claim hit.
5. Update the active-version note in the workspace (for example `resume/README.md`) so other skills pick up the new file, and tell the user the new `paths.master_resume` value to put in the config.

The six prompts:

1. **Recruiter audit.** Why would this be ignored in 10 seconds: weak positioning, vague impact, structure.
2. **Strategic weakness audit.** The three biggest strategic weaknesses for the target roles: the story not told, what is undersold, what is missing.
3. **Positioning and branding.** Is the target role unmistakable from the subhead and summary? Rewrite the summary to lead with the strongest verified hook.
4. **10-second scan.** Restructure the top third so the strongest credentials show in a skim: section order, hierarchy, strongest bullet first.
5. **Executive tone.** Replace task language ("responsible for", "helped with") with ownership language without changing any fact.
6. **Achievement conversion.** Convert task bullets to situation, action, result. Numbers only from the metrics worksheet; where none exists use a bracketed placeholder such as [X%], never an invented number.

## Rules

- Numbers come only from the metrics worksheet or the master resume, verbatim. Check `claims_limits` before any rewrite.
- Never change an employer, title, date, scope, team size or result.
- Keep within the page limit and verify with a PDF conversion when the tools exist; otherwise say "not measured".
- ATS-friendly here means formatting guidance only (plain headings, no text boxes, readable text layer). Nobody can promise how an employer's ATS will rank a resume.
- Audit what is on the page; do not credit experience the resume does not show.
