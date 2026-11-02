"""Build the Word version of the chapter from chapter_draft.md, laid out to the book editors'
instructions for chapters not using the Springer template:

  - one column, US Letter, 1-inch margins, Times New Roman 10 pt, single spacing, no spacing
    before or after paragraphs, no page numbers, headers or footers;
  - title, authors (corresponding author marked *), affiliation and e-mails centred at the top;
  - unnumbered Abstract and Keywords; sections I, II, ... (Heading 1), subsections A, B, ...
    (Heading 2); one blank line after each section;
  - figure titles centred directly under the figure, one blank line before and after each figure;
    table titles centred directly above the table; no figure or table taller than a page;
  - equations as Word equations (OMML), numbered on the right;
  - references without blank lines between them.

Draft-only notes (block quotes) and file references in back-ticks are left out.

Run from the repository root:
    .venv/bin/python chapter/build_docx.py
Writes chapter/sarkar.docx (the corresponding author's last name, as the editors ask).
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chapter" / "chapter_draft.md"
OUT = ROOT / "chapter" / "sarkar.docx"
FIGS = ROOT / "outputs" / "sepsis" / "figures"
FONT = "Times New Roman"
TEXT_WIDTH = Inches(6.5)
FIG_WIDTH = Inches(6.2)
FIG_MAX_HEIGHT = Inches(5.6)   # tall app screenshots are scaled down to this height


def set_font(style, size, bold=None, italic=None):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(k), FONT)
    for k in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):   # theme fonts win otherwise
        fonts.attrib.pop(qn(k), None)


def no_spacing(style):
    pf = style.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(0), 1.0


def setup(doc):
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Inches(11), Inches(8.5)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(1))
    sec.header_distance = sec.footer_distance = Inches(0.5)
    st = doc.styles
    set_font(st["Normal"], 10)
    no_spacing(st["Normal"])
    for name, size, italic in (("Title", 14, False), ("Heading 1", 11, False), ("Heading 2", 10, False),
                               ("Heading 3", 10, True)):
        set_font(st[name], size, bold=True, italic=italic)
        no_spacing(st[name])
        st[name].paragraph_format.keep_with_next = True
    st["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for bdr in st["Title"].element.findall(".//" + qn("w:pBdr")):   # no rule under the title
        bdr.getparent().remove(bdr)
    set_font(st["Caption"], 10, bold=False, italic=False)
    no_spacing(st["Caption"])
    st["Caption"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for name in ("List Bullet", "List Number"):
        set_font(st[name], 10)
        no_spacing(st[name])


# ---------------------------------------------------------------- equations (LaTeX subset -> OMML)

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SYMBOLS = {"ge": "≥", "le": "≤", "tau": "τ", "delta": "δ", "alpha": "α", "ldots": "…", "in": "∈",
           "cdot": "·", "{": "{", "}": "}", "quad": " ", "qquad": "  ", ",": " "}
FUNCTIONS = {"min", "max", "Pr"}
TOKEN = re.compile(r"\\(?:text|mathrm|mathbf)\{[^{}]*\}|\\[A-Za-z]+|\\[{},]|[{}_^]|\s+|.")


def m_run(text, sty=None):
    """A math run; sty "p" (upright text, function names) or "b" (bold) are set as normal text,
    which Word and LibreOffice both keep upright."""
    if sty:
        bold = "<w:b/>" if sty == "b" else ""
        return (f'<m:r><m:rPr><m:nor/></m:rPr><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}"/>{bold}</w:rPr>'
                f'<m:t xml:space="preserve">{escape(text)}</m:t></m:r>')
    return (f'<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'
            f'<m:t xml:space="preserve">{escape(text)}</m:t></m:r>')


class TexToOmml:
    def __init__(self, tex):
        self.toks = [t for t in TOKEN.findall(tex) if not t.isspace()]
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def group(self):
        if self.peek() == "{":
            self.take()
            out = self.seq(stop="}")
            self.take()
            return out
        return self.atom()

    def seq(self, stop=None):
        out = []
        while self.peek() is not None and self.peek() != stop:
            t = self.peek()
            if t in ("_", "^") and out:
                base = out.pop()
                sub = sup = None
                while self.peek() in ("_", "^"):
                    if self.take() == "_":
                        sub = self.group()
                    else:
                        sup = self.group()
                e = f"<m:e>{base}</m:e>"
                if sub and sup:
                    out.append(f"<m:sSubSup>{e}<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup></m:sSubSup>")
                elif sub:
                    out.append(f"<m:sSub>{e}<m:sub>{sub}</m:sub></m:sSub>")
                else:
                    out.append(f"<m:sSup>{e}<m:sup>{sup}</m:sup></m:sSup>")
            else:
                out.append(self.atom())
        return "".join(out)

    def atom(self):
        t = self.take()
        if t == "{":
            out = self.seq(stop="}")
            self.take()
            return out
        if not t.startswith("\\"):
            return m_run(t)
        name = t[1:]
        if name == "frac":
            num, den = self.group(), self.group()
            return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"
        if name == "sum":
            sub = sup = ""
            while self.peek() in ("_", "^"):
                if self.take() == "_":
                    sub = self.group()
                else:
                    sup = self.group()
            body = self.group()
            return (f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>'
                    f"<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup><m:e>{body}</m:e></m:nary>")
        if name.endswith("}") and "{" in name[:-1]:   # \text{...}, \mathrm{...}, \mathbf{...}: one token, content as written
            cmd, content = name[:-1].split("{", 1)
            return m_run(content, "b" if cmd == "mathbf" else "p")
        if name == "hat":
            return f'<m:acc><m:accPr><m:chr m:val="̂"/></m:accPr><m:e>{self.group()}</m:e></m:acc>'
        if name in FUNCTIONS:
            return m_run(name, "p")
        if name in SYMBOLS:
            return m_run(SYMBOLS[name])
        raise ValueError(f"unsupported command {t}")


def omath(tex):
    body = TexToOmml(tex).seq()
    return parse_xml(f'<m:oMath xmlns:m="{M_NS}" xmlns:w="{W_NS}">{body}</m:oMath>')


def add_equation(doc, tex, number):
    """Centred equation with its number at the right margin."""
    p = doc.add_paragraph()
    p.paragraph_format.keep_together = True
    stops = p.paragraph_format.tab_stops
    stops.add_tab_stop(int(TEXT_WIDTH / 2), WD_TAB_ALIGNMENT.CENTER)
    stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    p._p.append(omath(tex))
    p.add_run(f"\t{number}")


# ---------------------------------------------------------------- text

# italics only between word boundaries, so "s* and f*" (targets) is never read as emphasis
INLINE = re.compile(r"(\*\*[^*]+\*\*|(?<![\w*])\*(?=[A-Za-z])[^*]+?(?<=[A-Za-z.])\*(?![\w*])|`[^`]+`)")
# subscripts written as x_i, τ_home, w_(1), d_min in running text
SUBSCRIPT = re.compile(r"(?<=[A-Za-zτδ])_(\([A-Za-z0-9]+\)|[A-Za-z0-9]+)")


def clean(text):
    text = re.sub(r"\s*\(`[^`]*`(?:, [^)]*)?\)", "", text)   # "(`file.csv`)" references
    text = text.replace("\\*", "*")
    return text


def add_text(par, text, size, bold, italic):
    parts = SUBSCRIPT.split(text)
    for k, part in enumerate(parts):
        if not part:
            continue
        r = par.add_run(part)
        r.bold, r.italic = bold or None, italic or None
        if k % 2:
            r.font.subscript = True
        if size:
            r.font.size = Pt(size)


def add_runs(par, text, size=None, bold=False):
    for part in INLINE.split(clean(text)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            add_text(par, part[2:-2], size, True, False)
        elif part.startswith("`") and part.endswith("`"):
            add_text(par, part[1:-1], size, bold, False)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            add_text(par, part[1:-1], size, bold, True)
        else:
            add_text(par, part, size, bold, False)


def blank(doc):
    doc.add_paragraph()


def borders(table):
    """Horizontal rules only: top, below the header, bottom (journal style)."""
    pr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge, val in (("top", "single"), ("bottom", "single"), ("insideH", "nil"),
                      ("insideV", "nil"), ("left", "nil"), ("right", "nil")):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), val)
        e.set(qn("w:sz"), "6")
        e.set(qn("w:color"), "000000")
        b.append(e)
    pr.append(b)
    for cell in table.rows[0].cells:
        tcpr = cell._tc.get_or_add_tcPr()
        tb = OxmlElement("w:tcBorders")
        e = OxmlElement("w:bottom")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "000000")
        tb.append(e)
        tcpr.append(tb)


def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    t = doc.add_table(rows=len(cells), cols=len(cells[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(cells):
        for j, c in enumerate(r):
            p = t.cell(i, j).paragraphs[0]
            add_runs(p, c, size=8.5, bold=(i == 0))
        # a table never breaks across pages: keep every row with the next
        for c in t.rows[i].cells:
            c.paragraphs[0].paragraph_format.keep_with_next = i < len(cells) - 1
    # column widths in characters: every column at least as wide as its longest word (so no word
    # is broken), the rest of the line shared in proportion to how much more each column wants
    ncol = len(cells[0])
    plain = [[re.sub(r"[*`]", "", c) for c in r] for r in cells]
    wide = lambda w: sum(1.45 if ch.isupper() else 1 for ch in w)   # capitals are wider
    minw = [max(wide(w) for r in plain for w in r[j].split() or [""]) + 3.2 for j in range(ncol)]
    pref = [max(min(max(len(r[j]) for r in plain), 60) + 3.2, minw[j]) for j in range(ncol)]
    budget = TEXT_WIDTH / Pt(8.5 * 0.55)   # characters of 8.5 pt type on one line
    if sum(pref) <= budget:
        weight = pref
    else:
        spare = max(budget - sum(minw), 0) / max(sum(pref) - sum(minw), 1e-9)
        weight = [m + (q - m) * spare for m, q in zip(minw, pref)]
    t.autofit = False
    for j, wt in enumerate(weight):
        w = int(TEXT_WIDTH * wt / sum(weight))
        t.columns[j].width = w
        for row in t.rows:
            row.cells[j].width = w
    borders(t)
    blank(doc)


def add_code(doc, block):
    """Algorithm box: one shaded, ruled cell in a monospaced font."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "F4F3EF")
    cell._tc.get_or_add_tcPr().append(shd)
    p = cell.paragraphs[0]
    p.paragraph_format.keep_together = True
    for k, ln in enumerate(block):
        r = p.add_run(ln.rstrip())
        r.font.name = "Courier New"
        r.font.size = Pt(7.5)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Courier New")
        if k < len(block) - 1:
            r.add_break()
    borders(t)
    blank(doc)


def figure_captions(lines):
    caps = {}
    for ln in lines:
        m = re.match(r"- \*\*Fig\. (\d+)\*\* \(`([^`]+)`\)\. (.*)", ln)
        if m:
            caps[int(m.group(1))] = (m.group(2), m.group(3))
    return caps


def add_figure(doc, num, file, caption):
    blank(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    w, h = Image.open(FIGS / f"{file}.png").size
    p.add_run().add_picture(str(FIGS / f"{file}.png"), width=min(FIG_WIDTH, int(FIG_MAX_HEIGHT * w / h)))
    c = doc.add_paragraph(style="Caption")
    r = c.add_run(f"Fig. {num}. "); r.bold = True
    add_runs(c, caption)
    blank(doc)


def main():
    lines = SRC.read_text(encoding="utf-8").splitlines()
    caps = figure_captions(lines)
    doc = Document()
    setup(doc)

    placed, pending = set(), []
    i, section, n_h1 = 0, None, 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("## "):
            section = s[3:]
        if section in ("Figures",) or s.startswith(">") or s == "---" or not s:
            i += 1
            continue
        if s.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            add_code(doc, block)
            i += 1
            continue
        if s.startswith("# "):
            doc.add_paragraph(s[2:], style="Title")
        elif section is None:   # authors, affiliation, e-mails: centred under the title
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, s)
        elif s.startswith("### "):
            doc.add_heading(s[4:], level=2)
        elif s.startswith("## "):
            if n_h1 or section == "Abstract":
                blank(doc)   # one blank line after the end of each section (and after the title block)
            n_h1 += 1
            h = doc.add_heading(s[3:], level=1)
            if section == "Abstract":
                h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif s.startswith("$$"):
            m = re.match(r"\$\$(.*)\$\$\s*\((\d+)\)", s)
            add_equation(doc, m.group(1).strip(), f"({m.group(2)})")
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i]); i += 1
            add_table(doc, rows)
            continue
        elif re.match(r"^\s*- ", ln):
            p = doc.add_paragraph(style="List Bullet")
            if ln.startswith("   "):
                p.paragraph_format.left_indent = Cm(1.3)
            add_runs(p, re.sub(r"^\s*- ", "", ln))
        elif re.match(r"^\s*\d+\. ", ln) and section != "References":
            n, rest = s.split(". ", 1)   # plain numbers: Word's list numbering would run on
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.9)
            p.paragraph_format.first_line_indent = Cm(-0.5)
            add_runs(p, f"{n}.\t{rest}")
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
        elif re.match(r"^\d+\. ", s) and section == "References":
            n, rest = s.split(". ", 1)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.7)
            add_runs(p, f"[{n}] {rest}")
        else:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_runs(p, s)
            if re.match(r"\*\*(Table \d+|Algorithm \d+)\.", s):   # title centred, kept with its table
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.keep_with_next = True
        # place each figure after the first block that cites it (once its section has started)
        for n in map(int, re.findall(r"Fig\. (\d+)", s)):
            if n in caps and n not in placed and n not in pending:
                pending.append(n)
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        block_ends = not nxt or nxt.startswith(("#", "|", "---"))
        if pending and block_ends and section not in ("References",):
            for n in sorted(pending):
                add_figure(doc, n, *caps[n])
                placed.add(n)
            pending = []
        i += 1
    doc.core_properties.title = "Calibrate, Adapt, or Block"
    doc.core_properties.author = "Amlan Sarkar; Md Tobibul Islam"
    doc.save(OUT)
    print(f"Wrote {OUT} ({len(placed)} figures: {sorted(placed)})")


if __name__ == "__main__":
    main()
