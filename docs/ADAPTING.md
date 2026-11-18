# Adapting to another role

**The Technical Program Manager (TPM) setup is only the worked example.** Nothing in the engine is specific to TPMs: the scorer, scope gate, ATS check, skill-gap report and tracker are driven by data. If you are a data science engineer, a product manager, a software engineer or anything else, you replace the role-specific parts and leave everything else alone.

## What you replace

1. **Config sections** in your `jobsearch.config.json`.
2. **Five short text files**, one per skill, each holding that skill's role wording.

| Config section | What it controls | TPM example |
|---|---|---|
| `targets.roles_primary`, `roles_also_consider` | Titles you want; feeds the LinkedIn general queries | Technical Program Manager, Senior TPM |
| `sources.*` search terms | The searches actually run | "Technical Program Manager {company}" |
| `title_exclusions` | Titles dropped before scoring (whole-word match) | scrum master, product marketing |
| `scoring.title_match`, `title_miss_penalty`, `level_words` | Points for a title that looks like your role and your seniority words | "program manager" +8 |
| `scoring.domain_families` | Keyword groups with points (capped by `domain_cap`) | silicon, NPI, hardware, data center |
| `scoring.negative_families` | Keyword groups that subtract | retail, advertising |
| `scope_gate` | Adjacent sub-fields you are not targeting; roles in them are capped at Stretch / Watch | design-side VLSI, ML platforms |
| `skill_vocabulary` | The skills the ATS check and gap report look for | NPI, ASIC, bring-up, Jira |
| `do_not_claim` and `claims_limits` | What your resume must never claim | PMP, Six Sigma Black Belt |
| `ats_generic_terms` | Generic job-description terms the ATS check reports as gaps (regex) | stakeholder, roadmap, jira |
| `tracker_generic_words` | Title words that never identify a requisition alone (added to the built-in seniority words) | technical program manager, tpm |
| `scoring.points` | Point values for the base score and the negative and pay adjustments | base 40, negative title 10 |
| `companies.*` | Your employers of interest, avoid list, staffing patterns | |

| Skill | File to replace | Holds |
|---|---|---|
| `job-search` | `skills/job-search/references/role-profile.md` | what strong evidence looks like, keyword traps, honest gaps |
| `tailor-application` | `skills/tailor-application/references/role-vocabulary.md` | the role's themes, phrases you may mirror, subhead shapes |
| `resume-review` | `skills/resume-review/references/role-checklist.md` | what a screener for the role scans for |
| `interview-prep` | `skills/interview-prep/references/role-question-bank.md` | behavioral and role scenarios |
| `profile-audit` | `skills/profile-audit/references/role-keywords.md` | headline and keyword guidance |

`interview-thank-you` and `setup-workspace` are role-independent.

## How, in order

1. Run `setup-workspace` and tell it your role, or copy `examples/sample-workspace/jobsearch.config.json` and edit it.
2. Rewrite the config sections above together. A half-converted config scores the wrong things. `skills/setup-workspace/references/role-adaptation.md` has a worked **Data Science Engineer** example (illustrative values: check them against real postings for your target jobs).
3. Rewrite the five reference files with the same kinds of statements for your role. Each starts with a note saying it is the TPM example; keep that note's pointer back to this page or remove it.
4. `python -m jobsearch check`, then run the search on a quick run and read the top ten with the scope gate in mind. If the wrong roles rise, adjust `domain_families` and `scope_gate`, not the code.
5. Rebuild the skill-gap report once you have a few saved job descriptions: `python -m jobsearch gaps report`.

## What does not change

The approval gates, the no-invented-numbers rule, the tracker and its confirmation rule, the dashboard, the CSV, the privacy scan and every script stay as they are.

## Check yourself

- Does every title in `roles_primary` match a `title_match` phrase? If not, your own target jobs get the miss penalty.
- Is every keyword in `domain_families` something a posting for your role would actually contain?
- Does `scope_gate.out_phrases` describe fields next to yours that you do not want, and `in_phrases` the signals your field uses?
- Does each `skill_vocabulary` pattern compile and match the way recruiters write it (`check` tests the regexes)?
