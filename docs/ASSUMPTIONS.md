# Assumptions

What the suite takes for granted. If one is false for you, the output is less reliable; the right-hand column says what to do.

| # | Assumption | If it is false |
|---|---|---|
| 1 | You connect and pay for your own sources (Apify, Indeed connector) and are allowed to use them | The search stops; nothing is simulated |
| 2 | A posting that appears in a run's own search results is open at that moment. Job pages are often not fetchable, so "open" is that evidence plus text checks for "closed", "filled" and past apply-by dates | Confirm a role is open on the employer's site before you apply |
| 3 | A keyword score is a useful first sort. It cannot read whether a description needs expertise you lack | The skill reads the top descriptions and records changes with reasons; you read them too |
| 4 | Your master resume and metrics worksheet are accurate and current | Tailoring copies your mistakes faithfully |
| 5 | You applied only when you tell the tracker you did. Building a package is not submitting it | A status the suite did not hear from you is simply not recorded |
| 6 | A job board's posting id is stable for a posting; reposts usually get a new id | Reposts are caught by company, similar title and text similarity, not by id alone |
| 7 | Company names appear on postings in recognisable forms; aliases in the config cover the variants | Add the alias; an unrecognised name scores as "no tier" |
| 8 | Your preferred area can be described by place words in the location text (`scoring.home_locations`) | Roles in unlisted nearby towns look out-of-area |
| 9 | Salaries, when listed, are annual USD amounts like `$150,000 - $210,000` or `$150K-$210K` | Other formats are treated as "not listed" |
| 10 | Postings are in English and use the field names of the LinkedIn actor (or the aliases listed in `docs/DATA_SCHEMAS.md`) | Map your source's fields to those names before extract |
| 11 | Dates are compared against the run date you pass, as calendar dates (no time zones) | An off-by-one day at the window edge is possible |
| 12 | One person uses one workspace | No locking: do not run two searches into the same folder at once |
| 13 | The role-specific parts of the config describe your role (the example is a TPM) | See `ADAPTING.md`; a TPM config run for another role scores the wrong things |
| 14 | An AI model writes drafts; you review them | You are responsible for every claim you send |
