"""Build the Word version of the chapter from chapter_draft.md.

Springer-style manuscript: A4, single column, Times New Roman 10 pt, numbered headings as written,
tables in 9 pt, each figure placed after the paragraph that first cites it, with its caption
from the draft's figure list. Draft-only notes (block quotes) and file references in back-ticks are
left out of the Word version.

Run from the repository root:
    .venv/bin/python chapter/build_docx.py
Writes chapter/CAB_Sepsis_Chapter.docx.
"""

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chapter" / "chapter_draft.md"
OUT = ROOT / "chapter" / "CAB_Sepsis_Chapter.docx"
FIGS = ROOT / "outputs" / "sepsis" / "figures"
FONT = "Times New Roman"
FIG_WIDTH = Cm(15.5)


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


def setup(doc):
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(2.5))
    st = doc.styles
    set_font(st["Normal"], 10)
    pf = st["Normal"].paragraph_format
    pf.space_after, pf.space_before, pf.line_spacing = Pt(4), Pt(0), 1.0
    for name, size, before in (("Title", 16, 0), ("Heading 1", 12, 14), ("Heading 2", 11, 10),
                               ("Heading 3", 10, 8)):
        set_font(st[name], size, bold=True, italic=False)
        st[name].paragraph_format.space_before = Pt(before)
        st[name].paragraph_format.space_after = Pt(4)
        st[name].paragraph_format.keep_with_next = True
    for bdr in st["Title"].element.findall(".//" + qn("w:pBdr")):   # no rule under the title
        bdr.getparent().remove(bdr)
    set_font(st["Caption"], 9, bold=False, italic=False)
    for name in ("List Bullet", "List Number"):
        set_font(st[name], 10)
        st[name].paragraph_format.space_after = Pt(2)


# italics only between word boundaries, so "s* and f*" (targets) is never read as emphasis
INLINE = re.compile(r"(\*\*[^*]+\*\*|(?<![\w*])\*(?=[A-Za-z])[^*]+?(?<=[A-Za-z.])\*(?![\w*])|`[^`]+`)")


def clean(text):
    text = re.sub(r"\s*\(`[^`]*`(?:, [^)]*)?\)", "", text)   # "(`file.csv`)" references
    text = text.replace("\\*", "*")
    return text


def add_runs(par, text, size=None, bold=False):
    for part in INLINE.split(clean(text)):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            r = par.add_run(part[2:-2]); r.bold = True
        elif part.startswith("`") and part.endswith("`"):
            r = par.add_run(part[1:-1])
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            r = par.add_run(part[1:-1]); r.italic = True
        else:
            r = par.add_run(part)
        if bold:
            r.bold = True
        if size:
            r.font.size = Pt(size)


def borders(table):
    """Horizontal rules only: top, below the header, bottom (journal style)."""
    tbl = table._tbl
    pr = tbl.tblPr
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
            p.paragraph_format.space_after = Pt(1)
            add_runs(p, c, size=8.5, bold=(i == 0))
    borders(t)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_code(doc, block):
    """Algorithm box: one shaded, ruled cell in a monospaced font."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "F4F3EF")
    cell._tc.get_or_add_tcPr().append(shd)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    for k, ln in enumerate(block):
        r = p.add_run(ln.rstrip())
        r.font.name = "Courier New"
        r.font.size = Pt(7.5)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Courier New")
        if k < len(block) - 1:
            r.add_break()
    borders(t)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figure_captions(lines):
    caps = {}
    for ln in lines:
        m = re.match(r"- \*\*Fig\. (\d+)\*\* \(`([^`]+)`\)\. (.*)", ln)
        if m:
            caps[int(m.group(1))] = (m.group(2), m.group(3))
    return caps


def add_figure(doc, num, file, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIGS / f"{file}.png"), width=FIG_WIDTH)
    c = doc.add_paragraph(style="Caption")
    r = c.add_run(f"Fig. {num} "); r.bold = True
    add_runs(c, caption)


def main():
    lines = SRC.read_text(encoding="utf-8").splitlines()
    caps = figure_captions(lines)
    doc = Document()
    setup(doc)

    placed, pending = set(), []
    i, section = 0, None
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
        elif s.startswith("### "):
            doc.add_heading(s[4:], level=2)
        elif s.startswith("## "):
            doc.add_heading(s[3:], level=1)
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
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, f"{n}.\t{rest}")
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
        elif re.match(r"^\d+\. ", s) and section == "References":
            n, rest = s.split(". ", 1)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.7)
            p.paragraph_format.first_line_indent = Cm(-0.7)
            add_runs(p, f"{n}. {rest}", size=9)
        elif s.startswith("Amlan Sarkar") or s.startswith("¹") or s.startswith("\\*"):
            p = doc.add_paragraph()
            add_runs(p, s, size=10 if s.startswith("Amlan") else 9)
        else:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_runs(p, s)
            if re.match(r"\*\*(Table \d+|Algorithm \d+)\.", s):   # keep a caption with its table
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
