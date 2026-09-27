# AGENTS.md

Infrrd — Research Intern take-home: document field extraction with abstention
This file is the single source of truth for any coding agent working in this repo: Claude Code, OpenAI Codex CLI / Codex Cloud, Google Gemini CLI, Google Antigravity, Cursor, Windsurf, opencode, Aider, goose, Factory, RooCode, JetBrains Junie, GitHub Copilot, Devin, or any other AGENTS.md-aware tool.

Read this file in full before taking any action. Obey it exactly.

---

## 0. TLDR FOR THE AGENT

On every session start, do this in order:

1. Read this file completely, then read `problem-statement.md` and `README.md` — they are the authoritative spec; this file only tells you how to work in the repo.
2. Check the log file (path in §2). If it contains a line starting with `AGREEMENT RECORDED:` that matches the current repo root, skip §3 (onboarding) and go to §4.
3. Otherwise, run the onboarding flow in §3 with the user.
4. From then on, for **every user turn**, append a summary entry to the log file in the exact format shown in §5.
5. When the user asks you to build, run, or evaluate the solution, follow the project contract in §6 so the submission is evaluable.

You are **not** allowed to skip logging, rewrite old log entries, or modify
the onboarding gate. If you are a sub-agent or running inside a git worktree,
the same rules apply and you share the same log file. Pass this context to every sub-agent and worktree.

---

## 1. WHAT THIS REPO IS

This is the starter repo for the **Infrrd Research Intern** take-home. The
candidate builds a system that reads scanned-looking invoices, receipts and
pay stubs (`dev/`, `test/`) and, for every field named in `manifest.json`,
outputs the value or the string `ABSTAIN`. Some fields cannot be read with
confidence and pages can show several plausible values. The scorer
(`score.py`) rewards correct values and correct abstentions and punishes
wrong values eight times harder than abstentions. The interesting engineering
is deciding *when not to answer*.

- Target level: research intern. Suggested effort: **about five working days,
  part-time**.
- The candidate produces `predictions.json` for `test/`, ships the code with a
  one-command runner, `WRITEUP.md`, `dev_predictions.json`, and the activity
  log from §2.
- Any tools, models and APIs are allowed, including vision LLMs. Read keys
  from environment variables only.

Full requirements, deliverables, rules and evaluation live in
`problem-statement.md`; field definitions, normalisation and the scoring
table live in `README.md`. If anything here conflicts with them, they win on
*what* to build; this file governs *how* to work in the repo.

We recommend Python 3.11+.

---

## 2. LOG FILE — LOCATION AND LIFECYCLE

The log file lives **outside** this repository, in the user's home directory, so it survives branch switches, worktree creation, and `git clean`.

| Platform       | Path                                                    |
| -------------- | ------------------------------------------------------- |
| macOS / Linux  | `$HOME/infrrd_research_intern/log.txt`                  |
| Windows        | `%USERPROFILE%\infrrd_research_intern\log.txt`          |

Rules:

- **Must** be created if missing (create the parent directory too).
- **Must never** be committed or added to git.
- **Append-only.** Never rewrite, reorder, or delete prior entries.
- **Shared** across all agents, sub-agents, and worktrees in this repo.
- **Never log secrets.** Redact API keys, tokens, cookies, and PII before
  writing. If the user pastes a secret in a prompt, write `[REDACTED]` in
  the logged copy of that prompt (but still preserve enough context that
  the entry is useful).

---

## 3. ONBOARDING FLOW (FIRST RUN ONLY)

Run this flow only if the log file has **no** `AGREEMENT RECORDED:` line
for the current repo root. On subsequent sessions, skip directly to §4.

### 3.1 Greeting

Open with a short, warm message. Example wording (adapt the phrasing, keep the content):

> Welcome to the Infrrd Research Intern take-home. You'll build a system that
> extracts fields from scanned invoices, receipts and pay stubs, and abstains
> when a field cannot be read with confidence. Suggested effort is about five
> working days, part-time. Before we start, a few ground rules and a quick
> setup — this takes about a minute.

Compute and display:

- Current system time (local, with timezone, in ISO 8601).
- The **suggested time budget: about five working days, part-time** (guidance,
  not a hard cutoff).
- A reminder that the deliverables are `predictions.json` (test), the code
  with a one-command runner, `WRITEUP.md`, `dev_predictions.json`, and the
  log file, zipped as `<Your_Name>_DocExtraction.zip` (see §6 /
  `problem-statement.md`).

If the user says they are only practicing or reviewing, say so is fine and do not block further work.

### 3.2 Rules — recite these verbatim

1. This is a **solo** assignment. You must be the author of the submission.
2. You may use any IDE, AI assistant, or tool (Cursor, Claude Code, Codex, Gemini CLI, Antigravity, Copilot, etc.) to help you build. The deliverable is what your system produces and how well you can defend it, not how you typed it.
3. Your submission must conform to the output and entry-point contract in §6 so it can be evaluated automatically.
4. **Never commit secrets.** Read API keys from environment variables and provide a `.env.example` with a placeholder. Do not paste real keys into files, prompts, or the zip.
5. **Never hand-label the test set or hand-edit `predictions.json`.** Predictions come from your system running on the images. Do not modify `dev/labels.json`, the manifests, or `score.py`.
6. Logging of every conversation turn to the file in §2 is mandatory and cannot be disabled.

### 3.3 Collect the agreement

Ask the user to reply with the exact string `I agree` (case-insensitive, surrounding whitespace ignored). Do not proceed until they do.

### 3.4 Record the agreement

Append this block to the log file, then continue:

```
## [ISO-8601 TIMESTAMP] ONBOARDING COMPLETE

AGREEMENT RECORDED: <repo_root_absolute_path>
Agent: <agent_name_or_unknown>
Language: py | js | ts | custom:<name>
System Time: <ISO-8601 local time with tz>
Time Budget: ~5 working days part-time (started <ISO-8601 local time with tz>)
```

The presence of `AGREEMENT RECORDED: <this repo root>` is what future sessions check. Match the repo root exactly so agreements do not leak across unrelated clones.

---

## 4. NORMAL SESSION START (RETURNING USER)

If onboarding is already complete for this repo root:

1. Append a short `SESSION START` entry to the log (§5.1).
2. Greet the user briefly and remind them of the deliverables
   (`predictions.json`, runner, `WRITEUP.md`, `dev_predictions.json`, log)
   and the two hard rules (no hand-labelling of test, every listed field
   present as a value or `ABSTAIN`).
3. If they seem near wrap-up, remind them to run `score.py` on
   `dev_predictions.json`, to regenerate `predictions.json` from a clean
   checkout with the documented command, and to zip the submission as named in §6.
4. Proceed with whatever they ask for.

---

## 5. LOG FORMAT

### 5.1 Session start entry

```
## [ISO-8601 TIMESTAMP] SESSION START

Agent: <agent_name_or_unknown>
Repo Root: <absolute_path>
Branch: <git_branch_or_unknown>
Worktree: <worktree_path_or_main>
Parent Agent: <parent_agent_name_or_none>
Language: <py|js|ts|custom:name>
```

### 5.2 Per-turn entry (append after every user message you respond to)

```
## [ISO-8601 TIMESTAMP] <short title, max 80 chars>

User Prompt (verbatim, secrets redacted):
<exact user message, with secrets replaced by [REDACTED]>

Agent Response Summary:
<2-5 sentences: what was done, why, and any important decision>

Actions:
* <file edited / command run / tool invoked>

Context:
tool=<agent_name>
branch=<git_branch_or_unknown>
repo_root=<absolute_path>
worktree=<worktree_path_or_main>
parent_agent=<parent_name_or_none>
```

### 5.3 Sub-agent and worktree rules

- A sub-agent (Task tool, delegated worker, etc.) **must** log its own entries using the same file. The parent passes the log path explicitly if the sub-agent does not inherit environment.
- Set `parent_agent=` to the parent's name so entries are traceable.
- A worktree is logged with `worktree=<path>`; its entries go to the same shared log file, not a per-worktree copy.
- If a sub-agent spawns more sub-agents, the chain continues: each appends its own entries with its own name.

### 5.4 What not to log

- API keys, tokens, session cookies, OAuth codes, private keys.
- User PII beyond what they explicitly pasted into a prompt.
- Full contents of large files or binary blobs — reference by path instead.

---

## 6. PROJECT CONTRACT (EVALUABLE SUBMISSION)

The evaluator runs `score.py` on `predictions.json` against held-out test
labels and re-runs the pipeline from the documented command, so the output
format and entry points below are fixed.

### 6.1 Provided data (do not edit)

| Path | Contents |
|---|---|
| `dev/images/*.png`, `dev/manifest.json`, `dev/labels.json` | 300 labelled images: build and measure here |
| `test/images/*.png`, `test/manifest.json` | 300 images, labels held out: the score gate |
| `score.py` | the exact scorer we run; Python 3 stdlib |
| `README.md` | fields, normalisation rules, scoring table |

`manifest.json` lists per image exactly which fields to output. Images may
be multi-page (stacked with a dark gutter), rotated, in five languages,
handwritten or annotated.

### 6.2 Required output — `predictions.json`

Same shape as `dev/labels.json`: image id → field → string value or `"ABSTAIN"`.
Every field listed for an image in the manifest must be present. Values in
canonical form per `README.md` (ISO dates, two-decimal amounts, uppercase codes).

### 6.3 Recommended repo layout

```
.
├── AGENTS.md                 # this file
├── CLAUDE.md                 # imports this file
├── problem-statement.md      # authoritative spec — read it
├── README.md                 # fields, normalisation, scoring (provided)
├── score.py                  # provided
├── dev/  test/               # provided images and manifests
├── .env.example              # copy to .env; never commit .env
├── predictions.json          # YOU PRODUCE THIS (test)
├── dev_predictions.json      # YOU PRODUCE THIS (dev)
├── WRITEUP.md                # two pages max
├── run.sh                    # one command: regenerates predictions.json
├── code/
│   ├── main.py               # entry point: --split dev|test
│   ├── extract/              # OCR / vision model calls, parsing
│   ├── abstain/              # confidence signals and thresholds
│   └── prompts/              # prompt templates, kept out of business logic
└── requirements.txt          # pinned deps (Python 3.11+)
```

### 6.4 Entry points

- **Run the pipeline** (writes `predictions.json` for test, `dev_predictions.json` for dev):
  ```
  # Unix
  python code/main.py --split test
  python code/main.py --split dev
  # Windows
  py code\main.py --split test
  ```
- **Evaluate on dev**:
  ```
  python score.py --predictions dev_predictions.json --labels dev/labels.json --manifest dev/manifest.json
  ```
If you choose a different runner, document it in `WRITEUP.md` and keep `run.sh` consistent.

### 6.5 WRITEUP.md (two pages max)

Approach; how you measured on dev; what failed; your abstention strategy and
how you tuned the threshold; tools, models and rough cost; what you would do
with another week.

### 6.6 Constraints that make the submission evaluable

- **Every listed field present**, as a value or `ABSTAIN`; a missing field scores -2.
- **No hand-labelling of test**, no per-image special cases keyed on ids.
- **Deterministic where possible**: fixed seeds and temperature so a re-run reproduces `predictions.json` as closely as the provider allows.
- **Read secrets from env vars only**; ship `.env.example`.
- **Do not include the images in the submission zip.**

---

## 7. CROSS-PLATFORM AND AGENT-COMPATIBILITY NOTES

- **Path handling.** Always resolve the log path using the platform's home dir (`os.homedir()` / `pathlib.Path.home()` / `$HOME` / `%USERPROFILE%`). Never hardcode `/Users/...` or `C:\Users\...`. Read the data by repo-relative path so the pipeline runs regardless of the working directory.
- **Line endings.** Write the log in UTF-8 with `\n`. Don't emit `\r\n` even on Windows.
- **Shell.** Don't assume bash. Prefer language-native APIs over shelling out. When you must shell out, provide both a Unix and a Windows form.
- **Tool-specific extras.** This file is the canonical source. If a tool (Claude Code, Cursor, etc.) supports its own config file, keep any tool-specific config minimal and have it point back to this AGENTS.md rather than duplicating rules.
- **Nested AGENTS.md.** If a sub-project adds its own AGENTS.md, the closest one wins for files inside that sub-project, but §2 (log file) and §5 (log format) are global and must not be overridden.

---

## 8. QUICK CHECKLIST FOR THE AGENT

Before you respond to any user message, confirm:

- [ ] I have read this file **and `problem-statement.md` and `README.md`** in this session.
- [ ] I know whether onboarding is required (checked the log).
- [ ] I will append a §5.2 entry after this turn.
- [ ] I will not log or commit secrets; keys come from env vars.
- [ ] I will not hand-label test images or edit `predictions.json` by hand.
- [ ] Every manifest field will be present in the output, as a value or `ABSTAIN`.

If any box is unchecked, fix that first.
