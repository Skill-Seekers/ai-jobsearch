---
name: profile-audit
description: Audits and rewrites LinkedIn profile sections (headline, About hook, full About, experience, SEO keywords, elevator pitch) for the candidate's target roles, with approval before anything is saved. Use when the user mentions LinkedIn, says "fix my LinkedIn", "rewrite my headline", "improve my About section", "LinkedIn SEO", "update my LinkedIn experience", or "write my elevator pitch".
---

# Profile Audit

A structured LinkedIn session, one section or a full overhaul. Every rewrite needs approval before saving. Role-specific keyword guidance is in `references/role-keywords.md` (the shipped example is a Technical Program Manager; replace it for another role, see `docs/ADAPTING.md`).

## Setup

Read `jobsearch.config.json` (target roles, `claims_limits`, `do_not_claim`, `paths.profile`), the master resume (the source of truth for facts) and any drafts in the profile folder. If the config is missing, run `setup-workspace`.

## The eight prompts

1. **Headline.** Lead with the strongest verified credential combination in 120 characters or fewer, optimized for search and stopping power.
2. **About hook.** The two or three sentences visible before "see more": who the candidate is, what they deliver, why they differ.
3. **Full build, approval mode.** Section by section (Headline, About, Experience per role, Skills, Featured), pausing for approval at each.
4. **About copywrite.** A complete About under 260 words: hook, core value, soft call to action.
5. **Experience rewrite.** LinkedIn-length bullets, outcome first, readable by a non-specialist recruiter; three to five per role.
6. **Full audit and rewrite.** Audit pasted profile text, then rewrite in one pass; flag keyword gaps, positioning issues and missing social proof.
7. **SEO and keywords.** Identify 15 to 20 keywords for the target roles (start from `references/role-keywords.md` and the config's `skill_vocabulary`), audit density, inject missing ones naturally and only where true.
8. **Elevator pitch.** A 30-second spoken version: who, what, what next. Conversational.

## Steps

1. Show the eight prompts and ask which to run; ask for current profile text if the user has it (they paste it; the suite never logs in to LinkedIn).
2. Run them one at a time. After each, show the rewrite and ask: use, modify, or skip.
3. Confirm before saving. Save approved output to `profile/linkedin-profile-YYYY-MM-DD.md`.

## Rules

- Never invent roles, titles, employers, dates or metrics. Every claim traces to the resume or the metrics worksheet.
- LinkedIn tone is a human voice, not a CV.
- Headline under 220 characters; About under 2,600.
- Respect `claims_limits` and `do_not_claim`.
