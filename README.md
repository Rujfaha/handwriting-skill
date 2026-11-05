# handwriting (agent plugin)

Learn a person's real handwriting from PDFs that contain their pen strokes, then write new text onto PDFs in it.
Strokes are copied as vectors (no font), so the result is the person's own ink.

Requires Python 3.9+ with `pip install pymupdf pillow`.

## Install

**Claude Code**:
```
claude plugin marketplace add <path-or-github-url>
claude plugin marketplace add Rujfaha/handwriting-skill
claude plugin install handwriting@handwriting
```
Commands: `/handwriting:learn <pdf...> [profile]`, `/handwriting:write <pdf> [questions] [profile]`.
The skill also triggers by itself ("fill this in my handwriting").

**Other agents** that read Agent Skills (`SKILL.md`): copy or link `skills/handwriting` into that agent's
skills folder (for example `~/.codex/skills/`, `~/.agents/skills/`, or a project's `.claude/skills/`), then ask
"learn my handwriting from X.pdf" / "fill X.pdf in my handwriting". Codex can also load this folder as a plugin
via `.codex-plugin/plugin.json`. Any agent without skills can still follow `skills/handwriting/SKILL.md` and run
`skills/handwriting/scripts/hw.py` directly.

## Files
- `skills/handwriting/SKILL.md` instructions (learn / write workflows, job format)
- `skills/handwriting/scripts/hw.py` the tool (`hw.py` alone prints help; `hw.py selftest`)
- Profiles are not shipped; learn your own with `/handwriting:learn`. They are stored in `~/.handwriting/profiles/` so plugin updates never erase them.

Privacy: a profile is a copy of someone's handwriting; keep profiles out of public repos (they are gitignored).

Responsible use: only learn handwriting you own or have permission to use; do not use it to forge signatures or submit work dishonestly.

## Credits

Created by Arkkarawin Rujiprach, Petchra Pra Jom Klao Scholarship, Computer Engineering (CPE), King Mongkut's University of Technology Thonburi (KMUTT)
