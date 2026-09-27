# Research Intern take-home: document field extraction with abstention

## The problem

You receive scanned-looking images of invoices, receipts and pay stubs. For
each image, `manifest.json` names the fields to extract. Build a system that
outputs each field's value, or the string `ABSTAIN` when the field cannot be
read with confidence. Some fields cannot be read with confidence, and, as
on real paperwork, a page can show several numbers or dates that look like
the answer but are not. The scorer rewards correct values and correct
abstentions, and punishes wrong values far more than abstentions.

This mirrors production document AI: the hard part is not reading clean
text, it is knowing when not to answer.

## What you get

```
dev/      300 images + labels.json + manifest.json   build and measure here
test/     300 images + manifest.json                 the score gate; no labels
score.py  the exact scorer we run (Python 3 stdlib)
README.md field definitions, normalisation rules, scoring table
AGENTS.md / CLAUDE.md  instructions your coding agent must follow
```

Documents are in English, German, French, Spanish or Dutch. Some are
handwritten, some are photographed on a desk, faxed, photocopied, scanned
sideways or upside down, annotated in pen, or several pages stacked into one
image. Field names and label formats are the same throughout.

## Deliverables

1. `predictions.json` for `test/` in the format in README.md. Every listed
   field must be present, with a value or `ABSTAIN`.
2. Your code, runnable end to end with one documented command from a clean
   checkout (a `run.sh` or `make predict` that regenerates `predictions.json`).
3. `WRITEUP.md`, two pages at most: your approach, how you measured yourself
   on dev, what failed, your abstention strategy and how you tuned it, and
   what you would do with another week.
4. `dev_predictions.json` and your `score.py` output on dev.
5. The AI-agent activity log (see below), unedited.

Zip the five items together with your code as `<Your_Name>_DocExtraction.zip`.
Do not include the images.

## Rules

- Any tools, models and APIs are allowed, including vision LLMs and coding
  agents. Say what you used and roughly what it cost.
- Do not hand-label test images and do not hand-edit `predictions.json`.
  The system must produce it.
- Do not redistribute the images.
- Budget: about five working days of part-time effort. Tell us what you
  actually spent.

## How we evaluate

| what | how |
|---|---|
| score on test | `score.py`, the mean points per field; wrong answers cost -2, abstentions -0.25, correct answers and correct abstentions +1 |
| engineering judgment | the write-up and code: did you measure before tuning, handle orientation and languages deliberately, and reason about when to abstain |
| use of AI | the agent log: what you delegated, what you verified, and where you overrode the agent |

A capable vision model, prompted well but without your engineering, scores
around 0.4 on test. Beating that clearly is the target. Read the field
definitions in README.md carefully; they say which of several plausible
values is the right one.

## AI-agent activity log

We ask you to work with a coding agent (Claude Code, Codex, Cursor or any
AGENTS.md-aware tool) and to submit its activity log. This is about
transparency, not judgement: it lets us see how you steer an agent, which is
part of what the internship is about.

How it works: `AGENTS.md` in this folder instructs the agent to log every
turn (your prompt, a short summary of what it did, the files and commands it
touched) to `~/infrrd_research_intern/log.txt` on macOS/Linux or
`%USERPROFILE%\infrrd_research_intern\log.txt` on Windows. The log holds
your prompts verbatim with secrets redacted; it never records file contents.

What you do:
1. Open this folder (the one containing `AGENTS.md`) as the project root in
   your tool. Do not move or delete `AGENTS.md`, `CLAUDE.md` or `.cursor/`.
2. Claude Code: run `claude` here; Codex: run `codex` here; Cursor: open the
   folder. On the first run the agent recites the ground rules and asks you
   to reply `I agree`.
3. Never paste real API keys into prompts.
4. When you finish, attach `log.txt` to your submission unedited, and name
   the tools you used in `WRITEUP.md`.

## Tips

- Score yourself on dev early and often; the scorer is exactly what we run.
- Look at the images before writing code. Filter dev by the fields you get
  wrong most.
- Abstain on purpose, not by accident: build a confidence signal and pick
  the threshold that maximises the dev score.
- Sanity-check what you extract against the document's own arithmetic and
  against the field definitions before you trust it.
