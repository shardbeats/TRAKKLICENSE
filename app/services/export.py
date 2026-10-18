"""Export service: MD + styled PDF (reportlab, no extra deps).

PDF design (legal-document look, light theme):
  - Cover page: brand line, centered title, gold rule, metadata table, disclaimer.
  - Body: navy section headings with rules, justified text, grey quote boxes,
    bullet/list indent, `**bold**` inline support, `---` rules.
  - Footer on every content page: folio · beat — page N.

Filenames safe, no personal data in logs.
"""
import re
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import LETTER, A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

INK = HexColor("#1a1a1a")
NAVY = HexColor("#1f2a44")
GOLD = HexColor("#b98a1d")
GREY = HexColor("#6b7280")
LIGHT_BG = HexColor("#f3f4f6")
LABEL_BG = HexColor("#e8eaf0")


def safe_name(s: str) -> str:
    from ..engine.policy import FILENAME_SEGMENT_MAX_LEN
    s = re.sub(r"[^\w\- ]+", "", s, flags=re.UNICODE).strip().replace(" ", "_")
    return s[:FILENAME_SEGMENT_MAX_LEN] or "license"


def _fname(beat: str, customer: str, date: str, ext: str, hash8: str = "", prefix: str | None = None, folio: str = "") -> str:
    from ..engine.policy import DEFAULT_BRAND
    prefix = (prefix or DEFAULT_BRAND).strip() or DEFAULT_BRAND
    base = f"{prefix}_{safe_name(beat)}_{safe_name(customer)}_{safe_name(date)}"
    if folio:
        base += f"_{safe_name(folio)}"
    if hash8:
        base += f"_{hash8}"
    return base + ext


def _unique_path(out_dir: Path, filename: str) -> Path:
    """FIX: same beat/customer/date used to silently overwrite .md/.pdf.
    Now appends _2, _3… so no export ever clobbers a previous sale file."""
    p = out_dir / filename
    if not p.exists():
        return p
    stem, suffix = p.stem, p.suffix
    n = 2
    while True:
        cand = out_dir / f"{stem}_{n}{suffix}"
        if not cand.exists():
            return cand
        n += 1


def export_md(text: str, out_dir: Path, beat: str, customer: str, date: str, hash8: str = "", footer: str = "", prefix: str | None = None, folio: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = _unique_path(out_dir, _fname(beat, customer, date, ".md", hash8, prefix, folio))
    body = text if not footer else text.rstrip() + "\n\n---\n" + footer + "\n"
    p.write_text(body, encoding="utf-8")
    return p


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _inline_md(s: str) -> str:
    """Escape + minimal inline markdown (`**bold**`)."""
    return _BOLD_RE.sub(r"<b>\1</b>", _esc(s))


def _styles():
    base = getSampleStyleSheet()
    title = ParagraphStyle("TLTitle", parent=base["Title"], fontName="Helvetica-Bold",
                           textColor=NAVY, fontSize=22, leading=26, alignment=1,
                           spaceAfter=6)
    brand = ParagraphStyle("TLBrand", parent=base["Normal"], fontName="Helvetica-Bold",
                           textColor=GREY, fontSize=9, leading=12, alignment=1,
                           spaceAfter=10)
    h1 = ParagraphStyle("TLH1", parent=base["Heading1"], fontName="Helvetica-Bold",
                        textColor=NAVY, fontSize=16, leading=20,
                        spaceBefore=14, spaceAfter=4, keepWithNext=True)
    h2 = ParagraphStyle("TLH2", parent=base["Heading2"], fontName="Helvetica-Bold",
                        textColor=NAVY, fontSize=12, leading=15,
                        spaceBefore=12, spaceAfter=4, keepWithNext=True)
    body = ParagraphStyle("TLBody", parent=base["Normal"], fontName="Helvetica",
                          textColor=INK, fontSize=10, leading=14.5,
                          alignment=4, spaceAfter=6)  # 4 = justified
    quote = ParagraphStyle("TLQuote", parent=body, fontName="Helvetica-Oblique",
                           textColor=GREY, fontSize=9.5, leading=13.5,
                           alignment=0, spaceAfter=2)
    bullet = ParagraphStyle("TLBullet", parent=body, leftIndent=18,
                            bulletIndent=6, spaceAfter=3)
    field = ParagraphStyle("TLField", parent=body, fontName="Helvetica-Bold",
                           textColor=NAVY, fontSize=10.5, leading=14,
                           spaceBefore=8, spaceAfter=2, keepWithNext=True)
    small = ParagraphStyle("TLSmall", parent=base["Normal"], fontName="Helvetica-Oblique",
                           textColor=GREY, fontSize=8.5, leading=11.5,
                           alignment=1, spaceBefore=4)
    evidence = ParagraphStyle("TLEvidence", parent=base["Normal"],
                              fontName="Helvetica-Oblique",
                              textColor=GREY, fontSize=8.5, leading=11.5,
                              alignment=1, spaceBefore=10)
    cell_label = ParagraphStyle("TLCellLabel", parent=base["Normal"],
                                fontName="Helvetica-Bold", textColor=NAVY,
                                fontSize=9.5, leading=12.5)
    cell_value = ParagraphStyle("TLCellValue", parent=base["Normal"],
                                fontName="Helvetica", textColor=INK,
                                fontSize=9.5, leading=12.5)
    return {"title": title, "brand": brand, "h1": h1, "h2": h2, "body": body,
            "quote": quote, "bullet": bullet, "field": field, "small": small,
            "evidence": evidence, "cell_label": cell_label, "cell_value": cell_value}


def _gold_rule(width="100%", thickness=1.2):
    return HRFlowable(width=width, thickness=thickness, color=GOLD,
                      spaceBefore=4, spaceAfter=8)


def _cover_story(cover: dict, st: dict, brand: str) -> list:
    story = [Spacer(1, 1.1 * inch)]
    story.append(Paragraph(_esc(f"{brand} — Beat License"), st["brand"]))
    story.append(Paragraph(_esc(cover.get("title", "BEAT LICENSE")), st["title"]))
    story.append(_gold_rule(width="35%"))
    story.append(Spacer(1, 10))
    rows = []
    for label, value in cover.get("rows", []):
        val = str(value).strip()
        if not val or val in ("()", "( )"):
            continue
        rows.append([Paragraph(f"{_esc(label)}", st["cell_label"]),
                     Paragraph(_inline_md(val), st["cell_value"])])
    if rows:
        t = Table(rows, colWidths=[1.5 * inch, 4.5 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LABEL_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, GREY),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, GREY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)
    story.append(Spacer(1, 14))
    story.append(Paragraph("<i>See following pages for full terms.</i>", st["small"]))
    story.append(PageBreak())
    return story


_LIST_RE = re.compile(r"^(\d+[.)]|[-*•])\s+(.*)$")


def _quote_box(text: str, st: dict):
    """Grey-background indented box for `>` markdown quotes."""
    inner = [[Paragraph(_inline_md(text), st["quote"])]]
    t = Table(inner, colWidths=[6.0 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 0, LIGHT_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    # emulate left accent border with a thin gold first column
    accent = Table([[Paragraph('<font color="#b98a1d">|</font>', st["quote"]), t]],
                   colWidths=[0.22 * inch, 6.0 * inch])
    accent.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return accent


def _body_story(text: str, st: dict) -> list:
    story = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            story.append(Spacer(1, 5))
        elif s in ("---", "***"):
            story.append(_gold_rule())
        elif s.startswith("# "):
            story.append(Paragraph(_inline_md(s[2:]), st["h1"]))
            story.append(_gold_rule())
        elif s.startswith("## "):
            story.append(Paragraph(_inline_md(s[3:]), st["h2"]))
        elif s.startswith("### "):
            story.append(Paragraph(_inline_md(s[4:]), st["h2"]))
        elif s.startswith(">"):
            story.append(_quote_box(s[1:].strip(), st))
        elif _LIST_RE.match(s):
            item = _LIST_RE.match(s).group(2)
            story.append(Paragraph(_inline_md(item), st["bullet"], bulletText="•"))
        elif set(s) <= {"_", "—", "-"} and len(s) >= 3:
            story.append(Spacer(1, 10))  # signature line: breathing room
            story.append(Paragraph(_esc(s), st["body"]))
        elif s.rstrip(":").isupper() and len(s) <= 40 and len(s) >= 3:
            story.append(Paragraph(_inline_md(s), st["field"]))  # e.g. LICENSOR / PRODUCER
        else:
            story.append(Paragraph(_inline_md(s), st["body"]))
    return story


def _footer_canvas(brand_line: str, folio: str, beat: str):
    def _draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.6)
        canvas.line(doc.leftMargin, doc.bottomMargin - 14,
                   doc.pagesize[0] - doc.rightMargin, doc.bottomMargin - 14)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(GREY)
        left = f"{brand_line}" + (f"  ·  {folio}" if folio else "")
        canvas.drawString(doc.leftMargin, doc.bottomMargin - 26, left[:90])
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin,
                              doc.bottomMargin - 26, f"{beat[:40]}  —  p. {doc.page}")
        canvas.restoreState()
    return _draw


def export_pdf(text: str, out_dir: Path, beat: str, customer: str, date: str, hash8: str = "", footer: str = "", prefix: str | None = None, pagesize: str = "LETTER", folio: str = "", cover: dict | None = None, brand: str | None = None) -> Path:
    # brand is keyword-only in practice (appended last): None falls back to the
    # filename prefix, preserving the previous look for existing callers/tests.
    from ..engine.policy import DEFAULT_BRAND
    prefix = (prefix or DEFAULT_BRAND).strip() or DEFAULT_BRAND
    brand = (brand or prefix).strip() or prefix
    out_dir.mkdir(parents=True, exist_ok=True)
    p = _unique_path(out_dir, _fname(beat, customer, date, ".pdf", hash8, prefix, folio))
    page = A4 if str(pagesize).upper() == "A4" else LETTER
    doc = SimpleDocTemplate(str(p), pagesize=page,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.75 * inch,
                            title=f"{brand} - {beat}", author=brand,
                            subject=f"Beat license {folio}".strip())
    st = _styles()
    story: list = []
    if cover:
        story.extend(_cover_story(cover, st, brand))
    story.extend(_body_story(text, st))
    if footer:
        story.append(Spacer(1, 6))
        story.append(_gold_rule(width="30%"))
        story.append(Paragraph(_inline_md(footer), st["evidence"]))
    footer_fn = _footer_canvas(brand, folio, beat)
    if cover:
        # cover page: brand footer only (no page number)
        def _cover_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(GREY)
            canvas.drawCentredString(doc.pagesize[0] / 2, doc.bottomMargin - 26,
                                    f"{brand} — Beat License")
            canvas.restoreState()
        doc.build(story, onFirstPage=_cover_footer, onLaterPages=footer_fn)
    else:
        doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)
    return p
