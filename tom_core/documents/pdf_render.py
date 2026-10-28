"""Professional PDF reports (reportlab): cover page, contents, headings, tables, callouts, page numbers."""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle, XPreformatted)

from tom_core.documents.design import Palette
from tom_core.documents.spec import DocSpec


def _hex(h: str):
    return colors.HexColor("#" + h)


def _inline(text: str) -> str:
    t = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return re.sub(r"`([^`\n]+)`", r'<font face="Courier" color="#9D174D">\1</font>', t)


def _styles(pal: Palette):
    ss = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=10.5, leading=15,
                               textColor=_hex(pal.text), alignment=TA_JUSTIFY, spaceAfter=7),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20,
                             textColor=_hex(pal.primary), spaceBefore=14, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                             textColor=_hex(pal.secondary), spaceBefore=10, spaceAfter=5),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=30, leading=36, textColor=_hex(pal.primary)),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=14, leading=19, textColor=_hex(pal.secondary)),
        "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=10.5, leading=15, textColor=_hex(pal.muted)),
        "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=10.5, textColor=_hex(pal.accent)),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9.5, leading=12, textColor=_hex(pal.text)),
        "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=colors.white),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8.8, leading=11.5, textColor=_hex("111827")),
        "toc": ParagraphStyle("toc", fontName="Helvetica", fontSize=11, leading=18, textColor=_hex(pal.text)),
    }


def _flow(blocks: List[Dict[str, Any]], st, pal: Palette, width: float) -> List[Any]:
    out: List[Any] = []
    for b in blocks:
        k = b["type"]
        if k == "heading":
            out.append(Paragraph(_inline(b["text"]), st["h2"]))
        elif k == "paragraph":
            out.append(Paragraph(_inline(b["text"]), st["body"]))
        elif k in ("bullets", "numbered"):
            items = [ListItem(Paragraph(_inline(it), st["body"]), leftIndent=12) for it in b["items"]]
            out.append(ListFlowable(items, bulletType="bullet" if k == "bullets" else "1", start="•" if k == "bullets" else 1,
                                    bulletColor=_hex(pal.accent), leftIndent=14))
        elif k == "table":
            data = [[Paragraph(_inline(str(h)), st["cellh"]) for h in b["headers"]]] + \
                   [[Paragraph(_inline(str(c)), st["cell"]) for c in row] for row in b["rows"]]
            t = Table(data, colWidths=[width / len(b["headers"])] * len(b["headers"]), repeatRows=1)
            style = [("BACKGROUND", (0, 0), (-1, 0), _hex(pal.primary)),
                     ("LINEBELOW", (0, 0), (-1, -1), 0.4, _hex("D1D5DB")),
                     ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5),
                     ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
            style += [("BACKGROUND", (0, r), (-1, r), _hex(pal.light)) for r in range(2, len(data), 2)]
            t.setStyle(TableStyle(style))
            out += [t, Spacer(1, 8)]
        elif k == "code":
            t = Table([[XPreformatted(b["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                                      st["code"])]], colWidths=[width])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _hex("F3F4F6")),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            out += [t, Spacer(1, 8)]
        elif k == "callout":
            t = Table([[Paragraph(f"<b>Key point:</b> {_inline(b['text'])}", st["body"])]], colWidths=[width])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _hex(pal.light)),
                                   ("LINEBEFORE", (0, 0), (0, -1), 3, _hex(pal.accent)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
            out += [t, Spacer(1, 8)]
    return out


def render_pdf(content: Dict[str, Any], spec: DocSpec, pal: Palette, path: str) -> Dict[str, Any]:
    st = _styles(pal)
    margin = 2.2 * cm
    width = A4[0] - 2 * margin
    title = content["title"]

    def page(canvas, doc):
        if doc.page == 1 and not content.get("letter"):
            canvas.saveState()
            canvas.setFillColor(_hex(pal.primary))
            canvas.rect(0, 0, 0.6 * cm, A4[1], fill=1, stroke=0)
            canvas.restoreState()
            return
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(_hex(pal.muted))
        canvas.drawRightString(A4[0] - margin, A4[1] - 1.3 * cm, title[:90])
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc.page}")
        canvas.setStrokeColor(_hex(pal.accent))
        canvas.setLineWidth(0.8)
        canvas.line(margin, A4[1] - 1.45 * cm, A4[0] - margin, A4[1] - 1.45 * cm)
        canvas.restoreState()

    story: List[Any] = []
    if content.get("letter"):
        if spec.sender:
            story += [Paragraph(f"<b>{_inline(spec.sender)}</b>", st["h1"])]
        story += [Paragraph(f"{date.today():%B %d, %Y}", st["meta"]), Spacer(1, 14)]
        if spec.recipient:
            story += [Paragraph(f"To: {_inline(spec.recipient[:1].upper() + spec.recipient[1:])}", st["body"])]
        story += [Paragraph(f"<b>Subject:</b> {_inline(content['subject'])}", st["body"]), Spacer(1, 8),
                  Paragraph(f"Dear {_inline(spec.recipient.title()) if spec.recipient else 'Sir or Madam'},", st["body"])]
        story += _flow(content["sections"][0]["blocks"], st, pal, width)
        story += [Spacer(1, 12), Paragraph("Sincerely,", st["body"]), Spacer(1, 18),
                  Paragraph(f"<b>{_inline(spec.sender)}</b>", st["body"])]
    else:
        story += [Spacer(1, 6 * cm), Paragraph(spec.genre.upper(), st["kicker"]), Spacer(1, 8),
                  Paragraph(_inline(title), st["title"]), Spacer(1, 12)]
        if content.get("subtitle"):
            story.append(Paragraph(_inline(content["subtitle"]), st["sub"]))
        story.append(Spacer(1, 5 * cm))
        for line in (f"Prepared by {spec.sender}" if spec.sender else "",
                     f"Prepared for {spec.audience.title()}" if spec.audience else "", f"{date.today():%B %d, %Y}"):
            if line:
                story.append(Paragraph(line, st["meta"]))
        story += [PageBreak(), Paragraph("Contents", st["h1"])]
        story += [Paragraph(f"{i}.&nbsp;&nbsp;{_inline(s['heading'])}", st["toc"]) for i, s in enumerate(content["sections"], 1)]
        story.append(PageBreak())
        for i, s in enumerate(content["sections"], 1):
            body = _flow(s["blocks"], st, pal, width)
            story.append(KeepTogether([Paragraph(f"{i}. {_inline(s['heading'])}", st["h1"])] + body[:1]))
            story += body[1:]
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=margin, rightMargin=margin, topMargin=2.3 * cm,
                            bottomMargin=2.0 * cm, title=title, author=spec.sender or "TOM", subject=spec.topic)
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return {"path": path, "sections": len(content["sections"])}
