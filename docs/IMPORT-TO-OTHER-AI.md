# How to import ai-jobsearch into ChatGPT or Gemini

This guide explains how to download the public ai-jobsearch repo and give it to ChatGPT or Gemini so it can build a similar tool.

**Limit:** the Python tools, tests, and docs carry over to other AI platforms. The skill files use Claude's plugin format, so they won't run in ChatGPT or Gemini as-is. Those platforms would need the skills rewritten as their own instructions.

## Steps

1. Open https://github.com/Skill-Seekers/ai-jobsearch. The repo is public, so no sign-in is needed.
2. Click the green **Code** button, then **Download ZIP**.
3. Unzip the file, for example to a folder named `ai-jobsearch`.
4. Upload the files to ChatGPT or Gemini.
   - ChatGPT can take the ZIP directly in Advanced Data Analysis.
   - Gemini may not open a ZIP, so upload the key folders instead: `README.md`, `docs/`, `jobsearch/`, `skills/`, `tests/`, and `examples/`.
5. Paste this prompt:

   > "This is an open-source job-search workflow built as a Claude plugin, with a Python command-line tool, skill instructions, and docs. Read the README and the docs in `docs/`. I want to build a similar tool for [your platform / your role]. Explain the architecture, then propose a port that keeps the scoring, tracking, and privacy-scan logic in Python and rewrites the skills for [ChatGPT custom GPTs / Gemini / other]. Keep the approval gates and the no-invented-numbers rule. Start with a plan before writing code."

6. Check the output against the tests in `tests/`. Run `python -m unittest discover -s tests` on any code it produces.

## Privacy

Use only the sample data in `examples/` when working with an AI service. Don't upload your own resume, job-search tracker, or results.

## License

The repo is MIT-licensed. Keep the `LICENSE` file and the copyright notice in any copy you share.
