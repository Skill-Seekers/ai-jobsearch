# Role profile for judging descriptions (EXAMPLE: Technical Program Manager)

This file is the role-specific half of `job-search`. It is a **worked example**. For another role (for example a data science engineer) replace it with the same kinds of statements for that role; see `docs/ADAPTING.md`. It must agree with the scoring sections of `jobsearch.config.json`.

## What counts as strong evidence in a description (example)

- Program ownership from plan to launch across engineering, test, manufacturing and customers.
- Named program types the candidate has run: new product introduction, silicon bring-up and qualification, customer qualification with OEM or ODM partners.
- Tools and methods the candidate actually uses (Jira, Confluence, risk and dependency tracking, executive reporting).

## Traps (a keyword in the title that the description may contradict)

- "ASIC", "silicon" or "SoC" in the title for a role that requires years of design-flow, RTL or verification work: this is an engineering job with a program-manager title. Cap at Stretch / Watch with an `adjust` reason.
- "Program Manager" for supply-chain sourcing, facilities, data-center operations or IT service management: a different function.
- "Customer" in the title for a pure sales or support role.

## Honest gaps to name, not paper over (example)

State what the candidate does not evidence (a certification they do not hold, a customer tier they did not own) in the adjustment reason and in the summary. Keep this list in sync with `do_not_claim` in the config.

## For another role

Write the same three lists for your role: what strong evidence looks like, which title keywords are traps, which gaps you will name. Then update `scoring.domain_families`, `scope_gate` and `do_not_claim` so the engine agrees.
