---
name: handwriting
description: >
  Learn a person's real handwriting from PDFs that contain their pen ink (Goodnotes, Notability, OneNote,
  any app that exports ink as vector strokes), then write new text, answers, matrices, name and ID onto a PDF
  in that exact hand. Use when the user wants an assignment/worksheet/form filled "in my handwriting",
  sends a handwritten PDF to learn from, or runs /handwriting:learn or /handwriting:write.
---

# Handwriting

Everything goes through one script, `scripts/hw.py` inside this skill's folder (run it with the
Python that has PyMuPDF; on Windows that is usually `py`, elsewhere `python3`; `pip install pymupdf pillow`
if missing). Run `hw.py` with no arguments for the command list, `hw.py selftest` to check the install.

The ink is never faked with a font: every glyph is the person's own pen strokes, copied as vectors and only
scaled. So the output is only as good as the glyphs learned, and anything not learned is refused, not invented.

Profiles: `hw.py list`. The user's learned profiles live in `~/.handwriting/profiles/<name>/profile.json`
(survive plugin updates). Bundled ones live in `profiles/` here. Each profile folder may have a `style.md`:
**read it before writing**; it says how that person phrases answers.

## Learn (`/handwriting:learn <pdf> [more pdfs] [profile name]`)

1. `hw.py scan <pdf>` for each file. Only pages marked VECTOR INK can be learned. A scanned or photographed
   page (raster only) cannot: tell the user to export the notes from the app as PDF instead.
2. Pick the profile: an existing one to extend, or `hw.py new <name> "Full Name"`.
3. For the richest pages: `hw.py sheet <pdf> <page> sheet.png` (page with numbered boxes, to read the words)
   and `hw.py gallery <pdf> <page> gal.png` (each group alone; label shows id and height in pt). Look at both
   images. Groups are strokes that touch, so one group may be a letter, a word, or two letters.
4. Add glyphs: `hw.py add <profile> <key> <pdf> <page> <ids> --h <pt> [--drop <pt>]`.
   - `key`: one character (`a`, `R`, `7`, `(`, `∈`, `→`, `∧`, `∨`, `#`) or a whole token the person writes
     often (`Sol`, `sym`, `NAME`, `ID`). Several ids join pieces: `150,151` (stem + dot of an i).
   - `--h` is the height the glyph should have, `--drop` how far it hangs below the baseline. Keep one scale
     for the whole profile. Reference used by the bundled profile: x-height 4.3, digits / capitals /
     ascenders 7.0, descender letters h 6.6-7.6 with drop 2.4-3.2, parentheses 9.5 drop 1.5, `=` 2.5 drop -2.
   - `--rot` turns a glyph (e.g. a `v` turned -90 gives `>`). `--replace` drops earlier variants; without it
     the new one is added as a variant (variants rotate, which looks more natural).
   - Only take a group when you are sure what it is. Check the gallery cell, not just the sheet.
5. `hw.py palette <profile>` (all glyphs) and `hw.py palette <profile> "sample text"`; look at the PNG.
   Fix bad picks with `--replace`. A glyph that drags a stray dot or neighbour stroke must be re-picked.
6. Write `style.md` in the profile folder: how the person lays out answers (prefixes, abbreviations,
   end mark, language), seen from their notes. Tell the user which characters are still missing.

## Write (`/handwriting:write <pdf> [what to answer] [profile]`)

1. Read the task PDF text and render each page to an image; look at where the empty answer space is.
   Measure positions in PDF points (page.rect, `page.get_text('dict')` line boxes): 72 pt = 1 inch.
2. Solve the questions yourself and **verify every answer** (brute force, sympy, a quick script) before writing.
3. Read the profile's `style.md`. Phrase answers the way that person does and only with characters the profile
   has: `hw.py palette <profile>` shows them. Rephrase around gaps (e.g. variables a b c when x y z are missing).
4. Write a job file (JSON):
   ```json
   {"blocks": [{"page": 0, "x": 74, "y": 236, "pitch": 19, "lines": ["Sol R = { (1,1) , (1,2) }", ">Ref : (a,a) ∈ R ~ T"]}],
    "matrices": [{"page": 1, "x": 110, "y": 494, "rows": [[1,0],[0,1]]}]}
   ```
   - `x`,`y`: start of the first baseline (pt). `pitch`: line spacing (19-21 reads well at the bundled scale).
     Optional `k` scales the writing (1 = the person's natural size), `indent` for `>` lines (default 16).
   - Line syntax: tokens are separated by spaces and get a word gap; characters inside a token sit close
     (`(1,1)` is one token). `~` = wide gap. `>>` = jump to a second column (tab 215 pt from the line start),
     good for two-column answers. A leading `>` indents the line. Aliases: `in ∈`, `notin ∉`, `!= ≠`,
     `-> →`, `and ∧`, `or ∨`. `²` is a small raised 2. Built automatically when not learned: `8` (two of their
     0s), `:` (two dots), `≠` and `∉` (their `=`/`∈` with their `/`).
5. `hw.py write <profile> job.json <in.pdf> <out.pdf>`. Never overwrite the user's input file; write a new
   file next to it unless told otherwise. If it stops with "NOT WRITTEN: no glyph for ...", learn those or
   rephrase; never substitute a font.
6. Render the output pages and look: nothing overlapping printed text, no line off the page (the script warns),
   matrices aligned, readable spacing. Fix the job and rerun. Then tell the user what was written, what was
   built rather than taken from their ink, and anything not checked.

Keep outputs small: vector strokes add only a few hundred KB per document.
