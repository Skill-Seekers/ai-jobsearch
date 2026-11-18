---
name: interview-thank-you
description: Writes short, specific post-interview thank-you notes, one per interviewer, and saves each as a .docx (or markdown when no Word tooling exists). Use when the user says "write a thank you note", "draft a TU note", "thank you after my interview", "post-interview note", "follow up after interview", or names an interviewer and wants to send something after a conversation.
---

# Post-Interview Thank-You Notes

Produce a note that sounds genuine because it references what was actually discussed. This skill is role-independent. Read `jobsearch.config.json` for the sign-off name, email and file prefix; if it is missing, run `setup-workspace`.

## Gather first (ask only for what is missing)

1. Interviewer first and last name.
2. Company and role.
3. Two or three points the user wants to reinforce; rough bullets are fine, sharpen them without losing the user's voice.
4. Interview date (default: today).

Do not ask extra follow-ups. Make a reasonable reading of the points and draft immediately.

## Format

```
[MM/DD/YYYY]

Subject: Thank You – [Role Title] Interview

Hi [First Name],

Thank you for taking the time to speak with me [today/yesterday]. I appreciated the conversation and wanted to highlight a couple of points:

• [Point 1: specific to the interview]

• [Point 2: specific to the interview]

I look forward to the possibility of joining the team.

Best regards,
[Sign-off name]
[Email]
```

- Highlights are bullets when there are two or more.
- No filler ("I really enjoyed learning about", "It was a pleasure"). Short and sharp beats comprehensive.
- Each bullet names the actual topic discussed, not a generic platitude. If the user's points are vague, tighten them and say what you changed.
- Sign-off is three separate lines.

## Iterate, then save

Show the full note in chat and apply targeted edits (a sentence, a word, the tone) until the user approves.

Save each note as its own file in `interview/thank-you/`: `<FilePrefix>-<Company>-<InterviewerLastName> <MMDDYYYY>.docx`. Use the available Word tooling (a docx skill) with a bold date line and subject label, 11 pt body, US Letter, and real list formatting (never a typed "•"). If no Word tooling is available, save the same text as `.md` and say so. Confirm the file and ask "Ready for the next interviewer, or are we done?" Each interviewer gets a separate file.

## Using prep notes

If the user says "use my prep notes", read the relevant file in `interview/` and quote only what it contains.
