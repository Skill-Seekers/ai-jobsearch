---
name: tailor-application
description: Runs the full application loop for one job: save the job description (from a URL or a saved file), check it is not a repeat of an earlier requisition, analyze its signals, tailor the master resume and optionally write a cover letter with approval at every step, run the ATS check, and add a tracker entry. Use when the user says "apply to job", "I found a job at [company]", "tailor my resume for [company or role]", "save this JD", "write a cover letter for [company]", or gives a posting URL.
---

# Tailor Application

One application, one review gate at every decision. Never run this freehand. Role-specific wording guidance is in `references/role-vocabulary.md` (the shipped example is a Technical Program Manager; replace it for another role, see `docs/ADAPTING.md`).

## Setup

Run tools with `python3 <plugin root>/jobsearch <command>` from inside the workspace (`<plugin root>` is `${CLAUDE_PLUGIN_ROOT}` when set, otherwise the folder two levels above this skill's base directory, the one that holds `skills/` and `jobsearch/`). From the config take: file prefix, master resume, metrics worksheet, `claims_limits`, `do_not_claim`, `hard_rules`, folders, page limit (default 2). If `jobsearch.config.json` is missing, run `setup-workspace`.

## Guardrails (always)

- No fabrication: no invented KPIs, roles, titles, tools, certifications or outcomes.
- Numbers come only from the metrics worksheet or appear verbatim in the master resume.
- Nothing is written until the user types go (step 6). Present every change; never batch-approve.
- Never overwrite a file: bump the version or add a letter suffix.
- If the posting asks for something the resume does not evidence, flag it plainly and say what will not be claimed. Never paper over a gap.
- Obey every `claims_limits` and `do_not_claim` line however the posting words its requirements.

## The loop

### 1. Intake and save

Needs company and title, plus one of these inputs (ask once if anything is missing):

- **a posting URL**: retrieve it and keep only the description (no navigation or footers);
- **the job description pasted as text**;
- **a `.txt` or `.md` file** already in `paths.job_descriptions`, or attached in the chat (use the file as is; do not copy it);
- **a `.docx` or `.pdf`**: convert it to plain text first, then treat it as pasted text.

Many job sites, LinkedIn included, block fetching. If the fetch is blocked or garbled, say so and ask for the text instead; do not work around the block. Save to `<paths.job_descriptions>/<Company>_<Title>.txt` with a header (COMPANY, TITLE, SOURCE, JOB ID, REQ ID from the body, POSTED, LOCATION) then a line of `=====` then the text. Show the first 10 lines and ask "Right content? yes or paste corrections".

### 2. Repeat check (required; never skip, even for a saved JD)

Reposting and cloning are common; applying twice to the same requisition, especially after a decline, is worse than not applying.

`tracker dupes --jd <file> --company "<Company>" --title "<Title>" [--req-id <id>] [--link <url>]`

It lists tracker entries with the same requisition id, posting id, or company plus distinctive title words, and saved JDs at or above 85% text similarity. Exit code 1 means something was found. Rules:

- Over 85% similarity or a matching requisition id: STOP. Name the earlier application and its outcome and ask before continuing.
- Same company and similar title but a lower similarity: show the differences and confirm it is a new requisition.
- A matching title alone does not prove the same requisition, and a different title does not prove it is different; only text and ids settle it.

Record the finding in `tailoring-notes.md` under "Requisition check".

### 3. Signal analysis

Read the JD and the master resume together. Output: company and role; two or three core emphasis themes; exact JD phrases worth mirroring (only where the resume truthfully supports them); what maps well; gaps against the master; a suggested subhead; **hard gaps**. Then ask: "Does this read right?"

### 4. Plan and walk-through

A table of section, proposed change, JD signal driving it, with a rationale per row (say where no change is needed). The user approves, modifies or rejects each row. Then, one row at a time, show SECTION, BEFORE (exact text), AFTER, WHY and ask: approve, edit, or skip. If an edit deviates from the plan, flag it. If a change would require inventing something, say "This would require inventing X. Here is an alternative using real evidence." Keep an approved-changes log. Skills rows stay short enough not to wrap; every skill listed needs a visible bullet as evidence.

### 5. Cover letter (optional)

Ask: yes, no, later. If yes: header from the config (name, email, optional phone and LinkedIn; no home address), addressee with company and job id, a one to three sentence hook naming the role and strongest real signal, two or three signals each tied to a concrete resume example, a short close. Direct tone, no "I am excited to apply". Build from the most recent prior cover letter if one exists so fonts carry over. Show the full draft and take line edits.

### 6. Final gate and write

Basename `<FilePrefix>-<Company>-<Role>_mmddyy`; add a letter suffix if the tracker already has it. Show: number of resume changes, cover letter yes/no, basename, output files. Ask "Type go to write the files." Then write to `<paths.tailored>/<Company-Role>/`: resume, cover letter if any, and `tailoring-notes.md` (header, requisition check, JD signal summary, changes made, what was NOT changed, gaps flagged and not claimed, cover letter, PDF status). Re-open each file and assert every intended replacement is present and every string the tailoring removed is absent; report the result.

### 7. ATS check

`ats <tailored resume .docx> <saved JD> --md <folder>/ats-check.md`. It reports parse-safety (text boxes, images, tables, headers, standard headings), JD keyword coverage, and gaps. It never inserts anything: show the gaps and let the user decide; a term on `do_not_claim` appears under DO NOT ADD. Exit code 1 means the resume contains a do-not-claim term: fix it before going further. This is formatting guidance, not a prediction of any employer's ATS.

### 8. PDFs and page count (ask first)

Convert with LibreOffice headless only on a clear yes. Measure pages with `pdfinfo` even when PDFs are declined (convert to a scratch folder, report, delete). If no converter or `pdfinfo` is available, report the page count as "not measured"; never estimate. Over the limit: trim text before touching spacing; do not shrink margins to force a fit.

### 9. Tracker

`tracker add --company "<Company>" --title "<Exact title>" --jd-file <path> --folder <Company-Role> --keywords <discriminator words> [--req-id ..] [--source-job-id <id from the posting URL>]`

The entry starts `status: drafted`, `applied: false`. **Building a package is not submitting it.** Only when the candidate says they submitted, run `tracker update --id <id> --status applied --applied-date <date> --confirmed`; if the date is unknown, leave it unset rather than guess. Choose `--keywords` that discriminate (not the role name or seniority words; the list is `tracker_generic_words` in the config); two are required to match, so avoid keywords where one contains the other. Capture the posting id from the URL: the search matches on it first. Never delete a declined application; it prevents a reapply.

### Confirmation card

Company, role, req id, date, files created (mark which PDF to submit), measured page counts, up to five key changes, ATS result, and a checklist: open the docx and check the layout, confirm the employer's form accepts PDF, attach the files, then tell me when you have submitted so I can update the tracker.

## Partial modes

| User says | Run |
|---|---|
| "apply to job [URL]" | steps 1 to 9 |
| "save this JD [URL]" | step 1 and 2 |
| "tailor my resume for [saved JD]" | steps 2 to 9 |
| "analyze the JD" / "show the plan" | steps 3 / 3 and 4 |
| "write a cover letter for [company]" | step 5 |
| "check this resume against that JD" | step 7 |
| "mark [company] as [status]" | tracker update, only after the user confirms it |
| "show my applications" | `tracker report` and the Applications tab of the latest dashboard |
