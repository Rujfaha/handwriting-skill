#!/usr/bin/env python3
"""Handwriting kit: learn a person's real pen strokes from vector-ink PDFs (Goodnotes, Notability, OneNote exports)
and write new text onto PDFs with them. Strokes are copied 1:1 (only scaled), so the result is the person's own ink.

  hw.py list                                         profiles (yours in ~/.handwriting/profiles + bundled)
  hw.py new <name> ["Display Name"]                  empty profile in ~/.handwriting/profiles/<name>
  hw.py scan <pdf>                                   which pages hold vector ink
  hw.py gallery <pdf> <page> [out.png]               every stroke group drawn alone with its id (look at it, then `add`)
  hw.py sheet <pdf> <page> [out.png]                 the page itself with group ids boxed (context for reading words)
  hw.py add <profile> <key> <pdf> <page> <ids> --h H [--drop D] [--rot DEG] [--replace]
                                                     bake one glyph variant (ids: 12 or 12,13) into the profile
  hw.py palette <profile> [text] [out.png]           draw every glyph (or a sample text) to check the profile
  hw.py write <profile> <job.json> <in.pdf> <out.pdf>   write answer blocks onto a PDF
  hw.py selftest                                     tiny assert-based check

Needs: python 3.9+, PyMuPDF (pip install pymupdf). Pillow only for gallery/palette.
"""
import json, math, os, random, sys
import pymupdf

# ---------------------------------------------------------------- reading ink

def strokes(doc, pg):
    """coloured stroke paths = pen ink (black/grey paths are usually the printed page)."""
    out = []
    for d in doc[pg].get_drawings():
        c = d.get('color')
        if d['type'] != 's' or c is None or max(c) - min(c) < 0.15: continue
        if d['rect'].width > 120 or d['rect'].height > 60: continue   # long rules, big circles
        out.append(d)
    return out

def groups(doc, pg, gap=0.7):
    """strokes whose boxes (grown by gap pt) touch -> [(rect, [stroke idx])] in reading order."""
    S = strokes(doc, pg); n = len(S); par = list(range(n))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    R = [pymupdf.Rect(s['rect']) for s in S]
    for i in range(n):
        a = R[i] + (-gap, -gap, gap, gap)
        for j in range(i + 1, n):
            if a.intersects(R[j]): par[f(i)] = f(j)
    G = {}
    for i in range(n): G.setdefault(f(i), []).append(i)
    out = []
    for ids in G.values():
        r = pymupdf.Rect(R[ids[0]])
        for i in ids[1:]: r |= R[i]
        out.append((r, sorted(ids)))
    out.sort(key=lambda t: (round(((t[0].y0 + t[0].y1) / 2) / 14), t[0].x0))
    return out, S

def cmd_scan(pdf):
    doc = pymupdf.open(pdf)
    for p in doc:
        n = len(strokes(doc, p.number)); im = len(p.get_images())
        tag = 'VECTOR INK' if n > 20 else ('raster only (scan/photo: cannot learn strokes)' if im and n == 0 else '')
        print(f'page {p.number}: {n} ink strokes, {im} images  {tag}')

def cmd_gallery(pdf, pg, out=None, cols=18, cell=90):
    from PIL import Image, ImageDraw
    doc = pymupdf.open(pdf); pg = int(pg); G, _ = groups(doc, pg); page = doc[pg]
    rows = max(1, (len(G) + cols - 1) // cols)
    W = Image.new('RGB', (cols * cell, rows * cell), 'white'); D = ImageDraw.Draw(W)
    for k, (r, _) in enumerate(G):
        clip = r + (-1, -1, 1, 1); z = min(6, (cell - 22) / max(clip.width, clip.height, 0.1))
        pm = page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip)
        x, y = (k % cols) * cell, (k // cols) * cell
        W.paste(Image.frombytes('RGB', (pm.w, pm.h), pm.samples), (x + 2, y + 18))
        D.rectangle([x, y, x + cell - 1, y + cell - 1], outline=(200, 200, 200))
        D.text((x + 3, y + 2), f'{k}  h{r.height:.1f}', fill=(220, 0, 0))
    out = out or f'gallery_p{pg}.png'; W.save(out); print(out, len(G), 'groups (cell label: id, height pt)')

def cmd_sheet(pdf, pg, out=None):
    doc = pymupdf.open(pdf); pg = int(pg); page = doc[pg]; G, _ = groups(doc, pg)
    if not G: sys.exit('no vector ink on this page')
    for k, (r, _) in enumerate(G):
        page.draw_rect(r, color=(1, 0, 0), width=0.15)
        page.insert_text((r.x0, r.y0 - 0.4), str(k), fontsize=2.8, color=(1, 0, 0))
    xs = [r.x0 for r, _ in G] + [r.x1 for r, _ in G]; ys = [r.y0 for r, _ in G] + [r.y1 for r, _ in G]
    out = out or f'sheet_p{pg}.png'
    page.get_pixmap(dpi=300, clip=pymupdf.Rect(min(xs) - 5, min(ys) - 8, max(xs) + 5, max(ys) + 5)).save(out); print(out)

# ---------------------------------------------------------------- profile

USER_DIR = os.path.join(os.path.expanduser('~'), '.handwriting', 'profiles')   # learned profiles survive plugin updates
SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'profiles')

def resolve(name):
    """a path, or a profile name looked up in ~/.handwriting/profiles then in the skill's bundled profiles."""
    for c in (name, os.path.join(USER_DIR, name), os.path.join(SKILL_DIR, name)):
        if os.path.isfile(c): return c
        if os.path.isfile(os.path.join(c, 'profile.json')): return os.path.join(c, 'profile.json')
    sys.exit(f'no profile {name!r} (looked in {USER_DIR} and {os.path.normpath(SKILL_DIR)}); create one with: hw.py new {name}')

def cmd_new(name, display=None):
    d = os.path.join(USER_DIR, name); os.makedirs(d, exist_ok=True); f = os.path.join(d, 'profile.json')
    if os.path.exists(f): sys.exit(f'{f} already exists')
    json.dump({'name': display or name, 'ink': [0.0118, 0.2745, 0.5608], 'pen': 0.84, 'xh': 4.3, 'sources': [], 'glyphs': {}},
              open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f)

def cmd_list():
    for base in (USER_DIR, os.path.normpath(SKILL_DIR)):
        if not os.path.isdir(base): continue
        for n in sorted(os.listdir(base)):
            f = os.path.join(base, n, 'profile.json')
            if os.path.isfile(f):
                p = json.load(open(f, encoding='utf-8')); print(f'{n:16} {len(p["glyphs"]):3} glyphs  {p.get("name","")}  ({f})')

def load(path):
    path = resolve(path)
    with open(path, encoding='utf-8') as f: p = json.load(f)
    p['_path'] = path; return p

def save(p):
    path = p.pop('_path')
    with open(path, 'w', encoding='utf-8') as f: json.dump(p, f, ensure_ascii=False, separators=(',', ':'))
    p['_path'] = path

def bake(doc, pg, ids, rot=0.0):
    """group ids -> strokes as point lists, origin at the glyph's bottom-left, y down (PDF units)."""
    G, S = groups(doc, pg); st = [S[i] for g in ids for i in G[g][1]]
    paths = []
    for s in st:
        path = []
        for it in s['items']:
            if it[0] == 'l': path.append(['l'] + [c for p in it[1:3] for c in (p.x, p.y)])
            elif it[0] == 'c': path.append(['c'] + [c for p in it[1:5] for c in (p.x, p.y)])
        if path: paths.append(path)
    pts = [(seg[i], seg[i + 1]) for path in paths for seg in path for i in range(1, len(seg), 2)]
    if rot:
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts); a = math.radians(rot)
        def R(x, y): return cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)
        paths = [[[seg[0]] + [c for i in range(1, len(seg), 2) for c in R(seg[i], seg[i + 1])] for seg in path] for path in paths]
        pts = [(seg[i], seg[i + 1]) for path in paths for seg in path for i in range(1, len(seg), 2)]
    x0 = min(p[0] for p in pts); y1 = max(p[1] for p in pts)
    paths = [[[seg[0]] + [round(v - (x0 if i % 2 else y1), 3) for i, v in enumerate(seg[1:], 1)] for seg in path] for path in paths]
    return paths

def cmd_add(prof, key, pdf, pg, ids, h, drop=0.0, rot=0.0, replace=False):
    p = load(prof); doc = pymupdf.open(pdf)
    v = {'h': float(h), 'drop': float(drop), 'paths': bake(doc, int(pg), [int(i) for i in str(ids).split(',')], float(rot))}
    if replace or key not in p['glyphs']: p['glyphs'][key] = []
    p['glyphs'][key].append(v); save(p); print(f'{key!r}: {len(p["glyphs"][key])} variant(s)')

# ---------------------------------------------------------------- writing

ALIAS = {'in': '∈', 'notin': '∉', '!=': '≠', '->': '→', '=>': '→', 'and': '∧', 'or': '∨'}

class Pen:
    """write tokens with a profile. Spaces separate tokens; '~' wide space; '>>' jump to second column;
    a token that is a glyph key (e.g. 'Sol', 'NAME') is drawn whole, otherwise char by char; '²' = small raised 2."""
    def __init__(self, prof, page, x, base, k=1.0, seed=3):
        self.p, self.g, self.page = prof, prof['glyphs'], page
        self.x0, self.x, self.base, self.k = x, x, base, k
        sp = prof.get('spacing', {})
        self.GAP, self.LGAP, self.TOK = sp.get('gap', 1.5), sp.get('letter_gap', 0.6), sp.get('word', 3.6)
        self.WIDE, self.TAB = sp.get('wide', 9.0), sp.get('tab', 215)
        self.ink, self.pen = tuple(prof.get('ink', (0.01, 0.27, 0.56))), prof.get('pen', 0.84)
        self.sh = page.new_shape(); self.rnd = random.Random(seed); self.n = 0; self.missing = set()

    def draw(self, v, x, base, h=None, drop=None):
        h = (v['h'] if h is None else h) * self.k; drop = (v['drop'] if drop is None else drop) * self.k
        pts = [(seg[i], seg[i + 1]) for path in v['paths'] for seg in path for i in range(1, len(seg), 2)]
        bh = max(-min(q[1] for q in pts), 0.01); bw = max(q[0] for q in pts)
        s = h / bh; P = lambda a, b: pymupdf.Point(x + a * s, base + drop + b * s)
        for path in v['paths']:
            for seg in path:
                q = [P(seg[i], seg[i + 1]) for i in range(1, len(seg), 2)]
                self.sh.draw_line(*q) if seg[0] == 'l' else self.sh.draw_bezier(*q)
            self.sh.finish(color=self.ink, width=self.pen * min(1, max(self.k, .8)), lineCap=1, lineJoin=1, closePath=False)
        return bw * s

    def has(self, key): return key in self.g or key in ('8', ':', '²', '≠', '∉') and self._fallback_ok(key)

    def _fallback_ok(self, key):
        need = {'8': '0', ':': None, '²': '2', '≠': '=', '∉': '∈'}[key]
        return need is None or (need in self.g and (key not in '≠∉' or '/' in self.g))

    def glyph(self, key, raise_=0.0, shrink=1.0):
        if key not in self.g:
            if key == '8' and '0' in self.g: return self._eight()
            if key == ':': return self._colon()
            if key == '²' and '2' in self.g: return self.glyph('2', raise_=self.p.get('xh', 4.3) * 1.07, shrink=0.55)
            if key in ('≠', '∉') and '/' in self.g: return self._slashed('=' if key == '≠' else '∈')
            self.missing.add(key); self.x += 4 * self.k; return 0
        vs = self.g[key]; v = vs[self.n % len(vs)]; self.n += 1
        w = self.draw(v, self.x, self.base + self.rnd.uniform(-0.25, 0.25) * self.k, v['h'] * shrink, v['drop'] - raise_)
        self.x += w; return w

    def _eight(self):
        """no 8 learned: two of the person's own 0 loops stacked."""
        z = self.g['0'][0]; w1 = self.draw(z, self.x + 0.4 * self.k, self.base, 3.6, -3.4); w2 = self.draw(z, self.x, self.base, 3.8, 0)
        self.x += max(w1, w2); return max(w1, w2)

    def _colon(self):
        for dy in (0.6, 3.6):
            self.sh.draw_circle(pymupdf.Point(self.x + 0.6 * self.k, self.base - dy * self.k), 0.45 * self.k)
            self.sh.finish(color=self.ink, fill=self.ink, width=0)
        self.x += 1.4 * self.k; return 1.4 * self.k

    def _slashed(self, key):
        x = self.x; w = self.glyph(key); sl = self.g['/'][0]
        self.draw(sl, x + w / 2 - 1.4 * self.k, self.base, 7.0, 0.6); return w

    def write(self, text):
        for tok in text.split(' '):
            if tok == '>>': self.x = max(self.x + self.WIDE * self.k, self.x0 + self.TAB * self.k); continue
            if tok == '~': self.x += self.WIDE * self.k; continue
            if not tok: continue
            tok = ALIAS.get(tok, tok)
            if tok in self.g: self.glyph(tok)
            else:
                prev = ''
                for c in tok:
                    if prev: self.x += (self.LGAP if prev.isalpha() and c.isalpha() else self.GAP) * self.k
                    self.glyph(c); prev = c
            self.x += self.TOK * self.k

    def nl(self, pitch, indent=0): self.base += pitch * self.k; self.x = self.x0 + indent
    def done(self): self.sh.commit()

def block(prof, page, b):
    pen = Pen(prof, page, b['x'], b['y'], b.get('k', 1.0))
    for i, t in enumerate(b['lines']):
        if i: pen.nl(b.get('pitch', 19))
        ind, t = (b.get('indent', 16), t[1:]) if t.startswith('>') else (0, t)
        pen.x = pen.x0 + ind * pen.k; pen.write(t)
        if pen.x > page.rect.width - 18: print(f'WARNING line runs off the page (x={pen.x:.0f}): {t}')
    pen.done(); return pen

def matrix(prof, page, m):
    """digits in a grid with row/column labels (m['labels'], default 1..n) and drawn square brackets."""
    x, y, M = m['x'], m['y'], m['rows']; cw, rh = m.get('cw', 10.5), m.get('rh', 11.0)
    n = len(M[0]); labels = m.get('labels', [str(i + 1) for i in range(max(n, len(M)))])
    pen = Pen(prof, page, x, y)
    for j in range(n): pen.x = x + 14 + j * cw; pen.glyph(labels[j], shrink=0.75)
    for i, row in enumerate(M):
        pen.base = y + rh * (i + 1) + 2; pen.x = x; pen.glyph(labels[i], shrink=0.75)
        for j, v in enumerate(row): pen.x = x + 14 + j * cw; pen.glyph(str(v), shrink=0.85)
    yt, yb = y + 3.5, y + rh * len(M) + 4.5
    for xl, d in ((x + 10.5, 1), (x + 14 + n * cw - 1.5, -1)):
        pen.sh.draw_polyline([(xl + 2.2 * d, yt + 0.3), (xl, yt), (xl + 0.3 * d, (yt + yb) / 2), (xl, yb), (xl + 2.2 * d, yb - 0.2)])
        pen.sh.finish(color=pen.ink, width=pen.pen, lineCap=1, lineJoin=1, closePath=False)
    pen.done(); return pen

def cmd_write(prof, job, src, out):
    p = load(prof)
    with open(job, encoding='utf-8') as f: J = json.load(f)
    doc = pymupdf.open(src); missing = set()
    for b in J.get('blocks', []): missing |= block(p, doc[b['page']], b).missing
    for m in J.get('matrices', []): missing |= matrix(p, doc[m['page']], m).missing
    if missing:
        sys.exit(f'NOT WRITTEN: profile has no glyph for {sorted(missing)}. Learn them (add) or rephrase the text.')
    doc.save(out, garbage=4, deflate=True); print(out, os.path.getsize(out) // 1024, 'KB')

def cmd_palette(prof, text=None, out='palette.png'):
    p = load(prof); doc = pymupdf.open(); page = doc.new_page(width=612, height=792)
    if text: lines = text.split('\\n')
    else:
        keys = sorted(p['glyphs'], key=lambda k: (len(k) > 1, k)); lines, cur = [], []
        for k in keys:
            cur.append(k)
            if len(cur) == 14: lines.append(' '.join(cur)); cur = []
        lines.append(' '.join(cur))
    pen = block(p, page, {'x': 30, 'y': 40, 'lines': lines, 'pitch': 22})
    if pen.missing: print('missing glyphs:', sorted(pen.missing))
    page.get_pixmap(dpi=150, clip=pymupdf.Rect(0, 0, 612, min(792, pen.base + 30))).save(out); print(out)

def selftest():
    doc = pymupdf.open(); pg = doc.new_page(); sh = pg.new_shape()
    sh.draw_bezier((10, 20), (12, 10), (16, 10), (18, 20)); sh.finish(color=(0, 0.2, 0.6), width=0.8); sh.commit()
    doc2 = pymupdf.open('pdf', doc.tobytes())
    G, _ = groups(doc2, 0); assert len(G) == 1, G
    paths = bake(doc2, 0, [0]); ys = [seg[i] for seg in paths[0] for i in range(2, len(seg), 2)]
    assert abs(max(ys)) < 1e-6 and min(ys) < -5, ys            # bottom on baseline, drawn upward
    prof = {'glyphs': {'n': [{'h': 4.0, 'drop': 0, 'paths': paths}]}}
    out = pymupdf.open(); page = out.new_page(); pen = Pen(prof, page, 50, 100); pen.write('n nn q'); pen.done()
    assert pen.missing == {'q'}, pen.missing
    r = pymupdf.Rect(); [r.include_rect(d['rect']) for d in page.get_drawings()]
    assert abs(r.y1 - 100) < 0.6 and abs(r.height - 4.0) < 0.8, r  # scaled to h, sits on baseline
    print('selftest ok')

if __name__ == '__main__':
    try: sys.stdout.reconfigure(encoding='utf-8')   # Windows consoles default to a codepage without ∈ →
    except Exception: pass
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    c, rest = a[0], a[1:]
    if c == 'add':
        kw = {'h': None, 'drop': 0, 'rot': 0, 'replace': False}; pos = []
        i = 0
        while i < len(rest):
            if rest[i] == '--replace': kw['replace'] = True; i += 1
            elif rest[i].startswith('--'): kw[rest[i][2:]] = rest[i + 1]; i += 2
            else: pos.append(rest[i]); i += 1
        if kw['h'] is None: sys.exit('--h <height in pt> is required')
        cmd_add(*pos, **kw)
    else:
        {'list': cmd_list, 'new': cmd_new, 'scan': cmd_scan, 'gallery': cmd_gallery, 'sheet': cmd_sheet, 'palette': cmd_palette,
         'write': cmd_write, 'selftest': selftest}[c](*rest)
