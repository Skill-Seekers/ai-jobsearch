# Config reference: `jobsearch.config.json`

One file per candidate, at the root of your workspace. `setup-workspace` writes it from a short interview; you can also copy `examples/sample-workspace/jobsearch.config.json` and edit it. Keys beginning with `_` are comments. Run `python -m jobsearch check` after any edit.

**Enforced** means a tool reads the key and acts on it. **Guidance** means a skill reads it to shape its behaviour (and you can edit it freely) but no tool enforces it.

The shipped values describe a fictional Technical Program Manager in Austin. To use another role, replace the role-specific sections; see [ADAPTING](ADAPTING.md).

| Section | Holds | Used by | Kind |
|---|---|---|---|
| `schema_version` | `"1.0"` | `check` | enforced |
| `candidate` | `name` (required), `file_prefix` (output names, e.g. `ARivera`), `sign_off_name`, `email`, `phone`, `linkedin_url` | dashboard heading; `tailor-application`, `interview-thank-you` | enforced (name) / guidance |
| `paths` | `master_resume`, `metrics_worksheet`, `job_descriptions`, `tailored`, `tracker`, `search`, `interview`, `profile`; relative to the workspace root, never absolute and never containing `..` | every command and skill | enforced |
| `hard_rules`, `claims_limits` | Rules never broken; things a resume or letter must never claim | every skill | guidance |
| `do_not_claim` | `[{term, aliases, reason}]` terms the resume must not contain | `ats`, `gaps` | enforced |
| `targets.roles_primary` | Titles you want (required, non-empty) | `check`; skills | enforced (non-empty) |
| `targets.roles_also_consider`, `roles_exclude`, `levels_target`, `levels_exclude`, `functions_in_scope`, `locations_preferred`, `work_modes`, `location_rule` | Your targets in words | skills | guidance |
| `targets.compensation` | `minimum_salary` (below it: flagged, not hidden), `hard_drop_below_max` (a listed maximum under it: dropped) | `score`, `extract` | enforced |
| `targets.out_of_area_action` | `"filter"` drops non-remote roles outside `scoring.home_locations`; anything else keeps them with a penalty | `extract` | enforced |
| `companies.tiers` | `{"1": [{name, aliases}], "2": [...], "3": [...]}` | `score` (tier points), `queries` | enforced |
| `companies.dedicated_query_tiers` | Which tiers get their own LinkedIn query (batches are derived) | `queries` | enforced |
| `companies.avoid` | `[{name, aliases, reason, visibility}]`. `silent`: never shown anywhere. `filtered`: listed in the Filtered tab with the reason | `extract` | enforced |
| `companies.flag_only` | `[{name, aliases, note}]` shown with a flag (for example a former employer) | `score`, `dashboard` | enforced |
| `companies.staffing_patterns`, `consulting_patterns`, `defense_patterns`, `exclude_defense` | Lower-case name fragments to filter; defense is on or off | `extract` | enforced |
| `title_exclusions` | Whole-word title fragments that remove a role. Use phrases (`financial controller`, not `controller`) | `extract` | enforced |
| `sources` | `linkedin` (`enabled`, `actor`, `search_url`, `general_queries`, `company_query` with `{company}`, `company_f_WT`, `company_batch_size`), `indeed` (`searches`), `glassdoor` (`queries`), `dice`, `google_jobs`. At least one must be enabled | `queries`, `job-search` | enforced |
| `staging` | Optional: spread company batches over several days (`enabled`, `batches_per_day`) | `queries` | enforced |
| `scoring` | `posted_within_days`, `new_badge_days`, `buckets` (`strongest_min` > `strong_min` > `stretch_min` >= `hard_floor`), `base_cap`, `tier_points`, `home_locations`, `domain_families` (`{name: {keywords, points}}`), `domain_cap`, `negative_families`, `level_words`, `level_bonus`, `no_level_penalty`, `title_match` (`[{phrases, points}]`), `title_miss_penalty`, `home_bonus`, `remote_bonus`, `out_of_area_penalty`, `fresh_bonus`, `comp_bonus_min`, `comp_low_penalty_below` | `extract`, `score`, `dashboard` | enforced |
| `scope_gate` | `in_phrases`, `out_phrases` (per sub-field), `title_out` (a pattern per sub-field, required for each `out_phrases` key). A role with two or more distinct out-signals in one sub-field and more of them than in-signals is capped at Stretch / Watch | `score` | enforced |
| `liveness` | `closed_text_patterns`, `deadline_patterns` (one capture group: the date text) | `liveness` | enforced |
| `outputs` | `dashboard` (always built), `csv` (off by default) | `dashboard` | enforced |
| `skill_vocabulary` | `[{id, label, category, patterns, claim_term?}]` the skills the ATS check and the gap report look for | `ats`, `gaps` | enforced |

## What `check` enforces

- Required sections present; JSON valid.
- Every regex compiles (scope gate, liveness, skill vocabulary).
- Every path stays inside the workspace.
- `candidate.name` and `targets.roles_primary` are not empty.
- Bucket thresholds strictly descend and sit at or above the hard floor.
- Each domain family has keywords and numeric points; every `out_phrases` sub-field has a `title_out` entry.
- A company appears once across tiers, and is not both wanted (in a tier) and excluded.
- At least one source is enabled.
- Warnings (not errors): a resume or worksheet path that does not exist yet; no tier 1 or 2 companies.

## Matching rules worth knowing

- Company names are lower-cased and punctuation is dropped. A name or alias of four characters or fewer must match as a whole word; longer ones match as substrings.
- Title exclusions match whole words anywhere in the title.
- `avoid` beats everything: an excluded company is never scored.
