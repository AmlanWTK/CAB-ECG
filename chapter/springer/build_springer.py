"""Build the chapter in Springer Nature's Word template for book chapters, one section at a time.

The chapter is rewritten section by section. Each finished or draft section is a Markdown file in
sections/ (00_front.md, 01_introduction.md, ...); the build joins whatever sections exist, in file
order, so the Word file always shows the chapter as far as it has been written.

Layout comes from Springer Nature's "Word template for book chapters" (not committed: download it from
https://www.springernature.com/gp/authors/publish-a-book/manuscript-guidelines and extract
Author.dotm to chapter/springer_template/extracted/). The template gives the A4 page, Springer's text block,
its paragraph, heading, caption, table, equation and reference styles). The template's macros
are not used: they are stripped and the styles are applied directly. The book editors' own rules
are kept on top of the template:
  - title, authors (corresponding author marked *), affiliation and e-mails centred;
  - "Keywords:" (5-6) under the abstract; numbered sections referred to as "Section 4";
  - no page numbers, headers or footers;
  - figure titles centred under the figure, table titles centred above the table;
  - equations as Word equations; references in the editors' style, numbered [1], [2], ...

Citations are written [@key] or [@a; @b] and numbered in order of first appearance; references.md
holds the entries. Figures are listed in figures.md (same form as chapter_draft.md's figure list)
and placed after the paragraph that first cites them.

Run from the repository root:
    .venv/bin/python chapter/springer/build_springer.py
Writes chapter/springer/sarkar.docx. To share one section for review on its own (numbered from its
own citations), name the section files and an output file:
    .venv/bin/python chapter/springer/build_springer.py 01 chapter/springer/review/introduction.docx
"""

import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from build_docx import INLINE, SUBSCRIPT, borders, clean, omath  # noqa: E402

TEMPLATE = HERE.parent / "springer_template" / "extracted" / "Author.dotm"
BASE = HERE / "_base.docx"
OUT = HERE / "sarkar.docx"
FIGS = ROOT / "outputs" / "sepsis" / "figures_springer"   # drawn for the 117 mm text block (sepsis_figures.py --springer)
TEXT_WIDTH = Cm(11.7)        # the template's text block: 11906 - 2665 - 2608 twips
FIG_MAX_HEIGHT = Cm(15.0)

NO_BREAK = ("Learn-then-Test", "Risk-Controlling")
DROP_PARTS = ("word/vbaProject.bin", "word/vbaData.xml", "word/customizations.xml",
              "word/_rels/vbaProject.bin.rels", "customUI/customUI.xml")


# ---------------------------------------------------------------- template without macros

def base_document():
    """The template as a plain .docx: macro parts and the ribbon removed, styles kept."""
    with zipfile.ZipFile(TEMPLATE) as src, zipfile.ZipFile(BASE, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename in DROP_PARTS:
                continue
            data = src.read(item.filename)
            if item.filename == "[Content_Types].xml":
                text = data.decode()
                text = text.replace("application/vnd.ms-word.template.macroEnabledTemplate.main+xml",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml")
                text = re.sub(r'<Override PartName="/(?:word/vbaData\.xml|word/customizations\.xml|'
                              r'customUI/customUI\.xml|word/vbaProject\.bin)"[^>]*/>', "", text)
                text = re.sub(r'<Default Extension="bin"[^>]*/>', "", text)
                data = text.encode()
            elif item.filename == "word/settings.xml":
                # no automatic hyphenation: words split at line ends lose their hyphen when text
                # is copied from the PDF (Springer typesets from the Word file in any case)
                data = re.sub(r"<w:autoHyphenation[^>]*/>", "", data.decode()).encode()
            elif item.filename.endswith(".rels"):
                text = data.decode()
                text = re.sub(r'<Relationship [^>]*Target="[^"]*(?:vbaProject\.bin|vbaData\.xml|'
                              r'customizations\.xml|customUI\.xml)"[^>]*/>', "", text)
                data = text.encode()
            dst.writestr(item, data)
    return Document(str(BASE))


def no_numbering(par):
    """Switch off the template's automatic numbering on one paragraph (numbers are written out)."""
    ppr = par._p.get_or_add_pPr()
    num = OxmlElement("w:numPr")
    for tag, val in (("w:ilvl", "0"), ("w:numId", "0")):
        e = OxmlElement(tag)
        e.set(qn("w:val"), val)
        num.append(e)
    ppr.append(num)


# ---------------------------------------------------------------- text

class Citations:
    def __init__(self, path):
        self.entries = {}
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([a-z][a-z0-9]+): (.+)$", ln)
            if m:
                self.entries[m.group(1)] = m.group(2)
        self.order = []
        self.used = set()   # references cited in the sections being written out

    def number(self, text):
        def repl(m):
            nums = []
            for key in re.findall(r"@([a-z][a-z0-9]+)", m.group(0)):
                if key not in self.entries:
                    raise KeyError(f"no reference '{key}' in references.md")
                if key not in self.order:
                    self.order.append(key)
                self.used.add(key)
                nums.append(self.order.index(key) + 1)
            return "[" + ", ".join(map(str, sorted(nums))) + "]"
        return re.sub(r"\[@[^\]]+\]", repl, text)


def add_text(par, text, size, bold, italic):
    for term in NO_BREAK:   # names that must not be split at their hyphens
        text = text.replace(term, term.replace("-", "\u2011"))
    for k, part in enumerate(SUBSCRIPT.split(text)):
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


# ---------------------------------------------------------------- blocks

def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    t = doc.add_table(rows=len(cells), cols=len(cells[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(cells):
        for j, c in enumerate(r):
            p = t.cell(i, j).paragraphs[0]
            p.style = doc.styles["table"]
            p.paragraph_format.keep_with_next = i < len(cells) - 1
            add_runs(p, c, bold=(i == 0))
    # every column at least as wide as its longest word; the rest shared by how much more each wants
    ncol = len(cells[0])
    plain = [[re.sub(r"[*`]", "", c) for c in r] for r in cells]
    wide = lambda w: sum(1.45 if ch.isupper() else 1 for ch in w)   # capitals are wider
    minw = [max(wide(w) for r in plain for w in r[j].split() or [""]) + 3.2 for j in range(ncol)]
    pref = [max(min(max(len(r[j]) for r in plain), 60) + 3.2, minw[j]) for j in range(ncol)]
    budget = TEXT_WIDTH / Pt(8.5 * 0.55)
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
    gap = doc.add_paragraph(style="table")   # a little space before the text resumes
    gap.paragraph_format.space_before = Pt(4)


def add_code(doc, block):
    """Algorithm box: one shaded, ruled cell in a monospaced font, the width of the text block."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    cell.width = TEXT_WIDTH
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "F4F3EF")
    cell._tc.get_or_add_tcPr().append(shd)
    trpr = t.rows[0]._tr.get_or_add_trPr()   # the box never breaks across pages
    trpr.append(OxmlElement("w:cantSplit"))
    p = cell.paragraphs[0]
    p.style = doc.styles["table"]
    p.paragraph_format.keep_together = True
    for k, ln in enumerate(block):
        r = p.add_run(ln.rstrip())
        r.font.name = "Courier New"
        r.font.size = Pt(7)
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Courier New")
        if k < len(block) - 1:
            r.add_break()
    borders(t)
    gap = doc.add_paragraph(style="table")   # a little space before the text resumes
    gap.paragraph_format.space_before = Pt(4)


def add_equation(doc, tex, number):
    p = doc.add_paragraph(style="equation")   # the template's centre and right tab stops
    p.paragraph_format.keep_together = True
    p.add_run("\t")
    p._p.append(omath(tex))
    p.add_run(f"\t{number}")


def add_figure(doc, num, file, caption):
    p = doc.add_paragraph(style="figure")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    w, h = Image.open(FIGS / f"{file}.png").size
    p.add_run().add_picture(str(FIGS / f"{file}.png"), width=min(TEXT_WIDTH, int(FIG_MAX_HEIGHT * w / h)))
    c = doc.add_paragraph(style="figure")
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(f"Fig. {num} ")
    r.bold = True
    add_runs(c, caption)


def figure_captions(path):
    caps = {}
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"- \*\*Fig\. (\d+)\*\* \(`([^`]+)`\)\. (.*)", ln)
            if m:
                caps[int(m.group(1))] = (m.group(2), m.group(3))
    return caps


# ---------------------------------------------------------------- document

def main():
    cites = Citations(HERE / "references.md")
    caps = figure_captions(HERE / "figures.md")
    doc = base_document()
    body = doc.element.body
    for el in list(body):              # the template's empty sample paragraph; keep the page setup
        if el.tag != qn("w:sectPr"):
            body.remove(el)

    files = sorted((HERE / "sections").glob("*.md"))
    # number the citations over the whole chapter first, so a section written out on its own
    # keeps the numbers it has in the chapter
    for f in files:
        cites.number(f.read_text(encoding="utf-8"))
    cites.used = set()
    if len(sys.argv) > 1:   # only the named sections, e.g. "01" or "01,02"
        files = [f for f in files if f.name.split("_")[0] in sys.argv[1].split(",")]
    lines = []
    for f in files:
        lines += f.read_text(encoding="utf-8").splitlines() + [""]

    placed, pending = set(), []
    section, after_heading, i = None, True, 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith(">") or s == "---":
            i += 1
            continue
        s = cites.number(s)
        if s.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            add_code(doc, block)
            after_heading = True
            i += 1
            continue
        if s.startswith("# "):
            p = doc.add_paragraph(style="Main_Title")
            no_numbering(p)
            p.paragraph_format.page_break_before = False
            p.paragraph_format.space_before = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, s[2:])
        elif section is None and not s.startswith("## "):
            # authors, then affiliation and e-mails, centred under the title
            p = doc.add_paragraph(style="author" if "*" in s and "@" not in s else "affiliation")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.left_indent = Cm(0)
            add_runs(p, s)
        elif s.startswith("## "):
            section = s[3:]
            if section in ("Abstract", "Keywords"):
                # the next paragraph, with the run-in heading the template uses
                i += 1
                while not lines[i].strip():
                    i += 1
                para = []
                while i < len(lines) and lines[i].strip():
                    para.append(lines[i].strip()); i += 1
                p = doc.add_paragraph(style="abstract" if section == "Abstract" else "keyword")
                r = p.add_run("Abstract " if section == "Abstract" else "Keywords: ")
                r.bold = True
                add_runs(p, cites.number(" ".join(para)))
                # abstract and keywords stay together on the title page: less space around the
                # abstract than the template's 24 pt, and the abstract kept with the keywords
                if section == "Abstract":
                    p.paragraph_format.space_before = Pt(12)
                    p.paragraph_format.space_after = Pt(6)
                    p.paragraph_format.keep_with_next = True
                else:
                    p.paragraph_format.space_before = Pt(0)
                continue
            if section == "References":
                i += 1
                continue
            m = re.match(r"(\d+) (.*)", section)
            p = doc.add_paragraph(style="heading 1" if m else "unheading1")
            if m:
                no_numbering(p)
            add_runs(p, section)
            after_heading = True
        elif s.startswith("### "):
            p = doc.add_paragraph(style="heading 2")
            no_numbering(p)
            add_runs(p, s[4:])
            after_heading = True
        elif s.startswith("$$"):
            m = re.match(r"\$\$(.*)\$\$\s*\((\d+)\)", s)
            add_equation(doc, m.group(1).strip(), f"({m.group(2)})")
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cites.number(lines[i])); i += 1
            add_table(doc, rows)
            after_heading = True
            continue
        elif re.match(r"^\s*- ", lines[i]):
            p = doc.add_paragraph(style="bulletitem")
            if lines[i].startswith("   "):
                p.paragraph_format.left_indent = Cm(1.3)
            add_runs(p, re.sub(r"^\s*- ", "", s))
        elif re.match(r"^\d+\. ", s):
            n, rest = s.split(". ", 1)
            p = doc.add_paragraph(style="bulletitem")
            no_numbering(p)
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.6)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.6))
            add_runs(p, f"{n}.\t{rest}")
        elif re.match(r"\*\*(Table|Algorithm) \d+\.\*\*", s):
            p = doc.add_paragraph(style="tablelegend")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, s.replace(".**", "**", 1))   # Springer: "Table 1" in bold, no full stop
        else:
            p = doc.add_paragraph(style="noindentpara" if after_heading else "para")
            add_runs(p, s)
            after_heading = False
        for n in map(int, re.findall(r"Fig\. (\d+)", s)):
            if n in caps and n not in placed and n not in pending:
                pending.append(n)
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if pending and (not nxt or nxt.startswith(("#", "|", "---"))):
            for n in sorted(pending):
                add_figure(doc, n, *caps[n])
                placed.add(n)
            after_heading, pending = True, []
        i += 1

    if cites.used:
        p = doc.add_paragraph(style="references")
        p.add_run("References")
        for k, key in enumerate(cites.order, 1):
            if key not in cites.used:
                continue
            p = doc.add_paragraph(style="reference")
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.6)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(0.6))
            add_runs(p, f"[{k}]\t{cites.entries[key]}")

    doc.core_properties.title = "Calibrate, Adapt, or Block"
    doc.core_properties.author = "Amlan Sarkar; Md Tobibul Islam"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    BASE.unlink()
    print(f"Wrote {out}: {len(files)} section files, {len(cites.used)} references, figures {sorted(placed)}")


if __name__ == "__main__":
    main()
