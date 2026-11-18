# Build process

How this repo is built, checked and released. It is written so another maintainer can repeat it.
The privacy gate (section 2) is a hard stop: nothing is released until it passes.

## 1. Phases

| # | Phase | Output | Done when |
|---|---|---|---|
| 1 | Decisions | Audience, platforms, tools, license, name | Recorded in this file |
| 2 | Privacy gate set up | `tools/privacy_scan.py`, a private denylist kept outside the repo | `selftest` passes and the denylist is built |
| 3 | Inventory | Every source skill, command and tool marked keep, merge or drop | A table with a reason per row |
| 4 | Architecture | One config schema, folder layout, data schemas, tool interfaces | Reviewed by the owner |
| 5 | Port the tools | One `jobsearch` package with a single CLI, tests on fictional data | Tests pass; no personal paths or data |
| 6 | Rebuild the skills | Slim `SKILL.md` files that call the tools | Each skill runs on the sample workspace |
| 7 | Documentation | README, requirements, assumptions, scope (in and out), instructions, limits, changelog | Reads cleanly to someone who has never seen the project |
| 8 | Verification | Privacy scan, end-to-end run of every skill and tool, independent review pass | Section 3 checklist all ticked |
| 9 | Package | Git-ready folder, MANIFEST, release notes | Owner reviews the manifest and diff |

Files are created, never copied wholesale from a working folder. The repo is assembled from the
generic plugin, rewritten skills, ported tools and a fictional sample workspace (see 2.1).

### Status of this version (0.2.0)

| # | Phase | State |
|---|---|---|
| 1 to 4 | Decisions, privacy gate, inventory, architecture | done |
| 5 | Port the tools | done: 11 commands, 48 tests, demo script |
| 6 | Rebuild the skills | written; mechanically linted against the CLI (`tests/test_skills.py`); **not run in a live session** |
| 7 | Documentation | written |
| 8 | Verification | privacy scan clean on the last synced copy (see the release checklist); live skill runs and CI matrix **pending** |
| 9 | Package | `tools/build_plugin.py` builds the `.plugin`; maintainer reviews MANIFEST and pushes to a private repo first |

## 2. Privacy gate

### 2.1 Rules
1. **Build up, not out.** A file enters the repo only because someone wrote or rewrote it for the repo.
   Working folders, trackers, rosters, resumes, metrics worksheets, job descriptions, dashboards,
   scraped postings and configs are never copied in. All example data is fictional.
2. **The denylist lives outside the repo.** It holds the real name, nicknames, email, phone, employers,
   customers, interviewers, recruiters, companies applied to, requisition and posting IDs, resume
   numbers, folder paths and tokens. `scan` refuses to run if the denylist is inside the folder
   it is scanning. `.gitignore` also blocks the common names.
3. **Fresh git history.** Initialise the repo clean; never carry history in from a working folder.
   Set `user.email` to the GitHub noreply address so personal email is not written into commits.
4. **Look inside files.** Resume and workbook files are archives. The scanner opens them (and
   archives inside archives), reads document author and last-modified-by fields, PNG text chunks,
   PDF author fields and EXIF markers, and checks file names.
5. **Humans review what machines cannot.** Images and PDFs are listed for a person to open. The owner
   reads the manifest and the diff before the first push, pushes to a **private** repo first, lets the
   host's secret scanning run, and only then makes it public.

### 2.2 Commands

```bash
# one-time: prove the scanner works
python tools/privacy_scan.py selftest

# build the denylist where your real files are (output goes OUTSIDE the repo)
python tools/privacy_scan.py build-denylist --out ../_private/denylist.txt \
    --seed ../_private/private_terms.txt \
    --tracker path/to/applied_tracking.json \
    --resume path/to/master_resume.docx \
    --metrics path/to/metrics_worksheet.docx

# scan before every release (exit 0 = clean, 1 = findings)
python tools/privacy_scan.py scan . --denylist ../_private/denylist.txt --report ../_private/scan_report.txt

# review exactly what will ship, and what changed since last time
python tools/privacy_scan.py manifest . --out ../_private/MANIFEST.txt --compare ../_private/MANIFEST.prev.txt
```

Use `--show` to print matched text (output is masked by default), `--strict` to fail on WARN as well,
`--generic-only` for the built-in checks without a denylist (secrets, emails, phone numbers, personal
paths, LinkedIn profile and posting links, private IPs).

### 2.3 What it checks

| Area | Examples | Severity |
|---|---|---|
| Your terms | Name, email, employers, companies, people, IDs, paths from the denylist | FAIL |
| Resume numbers | Dollar amounts, percentages, counts taken from the metrics worksheet | WARN (reviewed by eye) |
| Built-in patterns | API tokens and keys, personal folder paths, email addresses, phone numbers, LinkedIn profile and posting URLs | FAIL |
| Weaker signals | Requisition IDs, Apify run and dataset IDs, private IP addresses | WARN |
| File names | Terms in names; `.env`, keys, databases, logs; temp and OS junk | FAIL / WARN |
| Inside archives | `.docx`, `.xlsx`, `.pptx`, `.zip`, `.plugin`, nested; terms split across Word runs; zero-width characters | FAIL |
| Metadata | Document creator and last-modified-by, company, PDF author, PNG text chunks, EXIF and XMP | FAIL / WARN |
| Git | Author and committer emails and names, commit messages, branch names, file names in history, credentials in remote URLs | FAIL |
| Images and PDFs | Cannot be fully inspected | WARN: open and check |

### 2.4 Limits (read these)
- It finds what it knows to look for. A detail never added to the denylist, or an indirect identifier
  (for example a rare job title plus a date), can pass. That is why rule 1 matters more than the scan.
- Short terms (7 characters or fewer) match whole words only, so a name glued to other letters,
  such as `JQuillResume`, may be missed unless the glued form is added to the denylist. A short
  capitalised term (for example a company called Globex) is case-sensitive to avoid flagging ordinary
  words and file names, so the same word in lower case is not caught.
- Text inside images, scanned PDFs and compressed PDF streams is not read.
- Passing the scan does not make a release safe by itself. Complete section 3.

## 3. Release checklist

- [ ] `selftest` passes.
- [ ] Denylist rebuilt from current files; seed file reviewed for nicknames and new employers.
- [ ] `scan` exits 0 on the repo folder, with the report saved outside the repo.
- [ ] Every WARN line opened and judged by a person.
- [ ] Every image and PDF opened and checked by eye.
- [ ] MANIFEST read in full; no file the maintainer did not expect.
- [ ] `git log --format='%an %ae %cn %ce'` shows only the noreply address and a public handle.
- [ ] Pushed to a private repo first; secret scanning shows no alerts.
- [ ] Sample workspace contains only fictional people, employers, numbers and links.
- [ ] README states the scraping terms-of-service responsibility and the other limits.
- [ ] Repo made public only after all of the above.

## 4. Decisions

| Decision | Choice | Notes |
|---|---|---|
| Audience | Any job seeker; TPM is the worked example profile | Generic core driven by one config file |
| Tools | Python package with one CLI, standard library only | Python 3.8+ |
| Platforms | Cowork plugin, also usable from Claude Code | Same `SKILL.md` files |
| License | MIT | |
| Name | `ai-jobsearch` | |
| Config | One JSON file per candidate | Validated by `jobsearch check` |
| Per-run output | **HTML dashboard on every run. CSV report optional, off by default** | Turn the CSV on with `"outputs": {"csv": true}` in the config or the `--csv` flag. Neither output needs a library. The CSV opens in any spreadsheet app. It is UTF-8 with a byte-order mark so Excel shows accents correctly, and cells that start with `=`, `+`, `-` or `@` are prefixed with an apostrophe so a scraped job title can never run as a spreadsheet formula. No XLSX: it would need `openpyxl` and a second code path to test |
