---
name: interview-prep
description: Runs an interview prep session grounded in the candidate's real resume and metrics — behavioral STAR practice, leadership-principles mapping, role-specific technical scenarios, a full mock interview, work on one question, or a recruiter pre-screen. Use when the user says "help me prep for an interview", "practice interview questions", "run a mock interview", "STAR practice", "behavioral questions", "recruiter screen prep", or "I have an interview".
---

# Interview Prep

Structured preparation where every answer is built from the candidate's real experience and numbers. The role-specific question types are in `references/role-question-bank.md` (the shipped example is a Technical Program Manager; replace it for another role, see `docs/ADAPTING.md`).

## Context to load

From `jobsearch.config.json`: name, master resume, metrics worksheet, `claims_limits`, `paths.interview`. From the workspace: `interview/interview-questions.md` (the question bank) and any prep file for the named company in `interview/<Company>/`. If the user names a company or role, also load its saved JD from `paths.job_descriptions`. If the config is missing, run `setup-workspace`.

## Prep types

- **a. Behavioral / STAR.** Open-ended questions in Situation, Task, Action, Result form using real examples; after each answer say what landed and what to sharpen.
- **b. Leadership principles.** Map real experiences to a company's published principles (Amazon's, for example). Ask for the story first, then structure it.
- **c. Role-specific scenarios.** The scenario types in `references/role-question-bank.md`: the user walks through their approach, then you give structured feedback.
- **d. Full mock.** A 45-minute simulation mixing behavioral, principle-based and role-specific questions; close with a debrief of strengths, gaps and recommended practice.
- **e. Specific question.** Draft a STAR answer together, refine it, then add the final version to the question bank.
- **f. Recruiter pre-screen.** A 20 to 30 minute screen. Build a one-page prep from the JD and the resume: the 60-second introduction, why this company and role, compensation and location answers from the config, the three strongest matches to the posting, the honest gaps and how to address each without overclaiming, and five questions to ask the recruiter. Then run a short mock screen.

## Steps

1. Load the context. If there is no metrics worksheet, say so and use only the numbers on the resume.
2. Ask which prep type (a to f). If the user named a company or role, tailor the questions to its JD.
3. In practice modes, ask one question at a time and wait for the answer.
4. Give specific feedback: quote the exact weak sentence and suggest a replacement; flag any missing metric or outcome.
5. Save new or refined answers to `interview/interview-questions.md` with the date.

## Rules

- Real experiences and real numbers only, from the metrics worksheet or resume. Never invent a scenario or outcome.
- Keep distinct stories distinct; record each story's canonical facts (what happened, the numbers, who did what) in the bank so later sessions do not drift.
- A story that needs a number the user does not have gets `[needs number]`, never an estimate.
- Respect `claims_limits` in every answer.
