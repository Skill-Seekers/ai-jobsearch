# Adapting the config to your role

The shipped example is a Technical Program Manager (TPM). Everything role-specific lives in `jobsearch.config.json`, so adapting means replacing config sections, not editing code. Replace the sections below together; a half-converted config scores the wrong things.

| Config section | What it controls | TPM example | What to write for your role |
|---|---|---|---|
| `targets.roles_primary`, `roles_also_consider` | Titles you want; also feeds the LinkedIn general queries | Technical Program Manager, Senior TPM | Your titles |
| `sources.*.general_queries`, `company_query`, `indeed.searches`, `glassdoor.queries` | The searches actually run | "Technical Program Manager {company}" | Your title keywords |
| `title_exclusions` | Titles dropped before scoring (whole-word match) | scrum master, product marketing, software engineer | Titles that share your keywords but are not your job |
| `scoring.title_match` + `title_miss_penalty` | Points for a title that looks like your role | "program manager" +8 | Your role words |
| `scoring.level_words` | Seniority words that earn the level bonus | senior, staff, principal, director | Your ladder |
| `scoring.domain_families` | Keyword groups with points; capped by `domain_cap` | silicon, npi, hw, data center | The skill areas your target jobs name |
| `scoring.negative_families` | Keyword groups that subtract | retail, advertising, clinical | Areas you do not want |
| `scope_gate` | `in_phrases` and per-domain `out_phrases`/`title_out`: roles in the wrong sub-field are capped at Stretch / Watch however many keywords match | design-side VLSI, ML platforms | Sub-fields adjacent to yours that you are not targeting |
| `skill_vocabulary` | The skills the ATS check and skill-gap report look for | NPI, ASIC, bring-up, Jira | The skills and tools your target postings ask for |
| `do_not_claim` | Terms the resume must never claim; the ATS check blocks them | PMP, Six Sigma Black Belt | Your own decisions |

Each `skill_vocabulary` item is `{"id", "label", "category", "patterns": [regex], "claim_term": optional}`. Patterns are case-insensitive regular expressions; `claim_term` links the skill to a `do_not_claim` term so the report can say "Decided no".

Five other skills carry role text in their own `references/` folder. Replace those files too:

| Skill | File |
|---|---|
| job-search | `skills/job-search/references/role-profile.md` |
| tailor-application | `skills/tailor-application/references/role-vocabulary.md` |
| resume-review | `skills/resume-review/references/role-checklist.md` |
| interview-prep | `skills/interview-prep/references/role-question-bank.md` |
| profile-audit | `skills/profile-audit/references/role-keywords.md` |

## Worked example: Data Science Engineer

Illustrative values, to show the shape. Check every one against real postings for the user's own target jobs before saving; do not treat this as a validated profile.

```json
"targets": {"roles_primary": ["Data Scientist", "Senior Data Scientist", "Machine Learning Engineer", "Data Science Engineer"],
            "roles_also_consider": ["Applied Scientist", "Analytics Engineer", "Research Engineer"]},
"title_exclusions": ["data entry", "data analyst intern", "sales engineer", "recruiter", "product manager", "marketing"],
"scoring": {
  "title_match": [{"phrases": ["data scientist", "data science", "machine learning", "ml engineer", "applied scientist"], "points": 8},
                  {"phrases": ["analytics engineer", "data engineer"], "points": 3}],
  "title_miss_penalty": 12,
  "level_words": ["senior", "staff", "principal", "lead"],
  "domain_families": {
    "ml": {"keywords": ["machine learning", "deep learning", "pytorch", "tensorflow", "scikit", "model training"], "points": 10},
    "experimentation": {"keywords": ["a/b test", "experiment design", "causal inference", "statistical modeling", "bayesian"], "points": 8},
    "data": {"keywords": ["sql", "spark", "airflow", "dbt", "feature store", "data pipeline"], "points": 6},
    "mlops": {"keywords": ["mlops", "model serving", "deployment", "monitoring", "kubernetes"], "points": 6}},
  "negative_families": {"reporting_only": ["dashboards only", "excel reporting", "data entry"]}},
"scope_gate": {
  "in_phrases": ["model training", "feature engineering", "experiment", "production ml"],
  "out_phrases": {"Pure BI / reporting": ["tableau (dashboard|developer)", "power ?bi", "reporting analyst"],
                  "Research / PhD only": ["phd required", "publication record", "novel architectures"]},
  "title_out": {"Pure BI / reporting": "bi (developer|analyst)|reporting", "Research / PhD only": "research scientist"}},
"skill_vocabulary": [
  {"id": "python", "label": "Python", "category": "Skill", "patterns": ["\\bpython\\b"]},
  {"id": "sql", "label": "SQL", "category": "Skill", "patterns": ["\\bsql\\b"]},
  {"id": "spark", "label": "Spark / distributed compute", "category": "Skill", "patterns": ["\\bspark\\b", "\\bdatabricks\\b"]},
  {"id": "expdesign", "label": "Experiment design / causal inference", "category": "Method", "patterns": ["a/b test", "experiment design", "causal inference"]},
  {"id": "mlops", "label": "MLOps / model serving", "category": "Method", "patterns": ["\\bmlops\\b", "model serving"]},
  {"id": "phd", "label": "PhD", "category": "Education", "patterns": ["\\bph\\.?d\\b"], "claim_term": "phd"}]
```

The same approach works for any role (product manager, software engineer, designer, analyst): list the titles, the skills postings name, the sub-fields you are not targeting, and the claims you will not make.
