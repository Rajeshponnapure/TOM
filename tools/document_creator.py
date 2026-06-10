"""
Professional Document Creator for TOM.

Creates production-quality:
  - Word documents (.docx)   via python-docx
  - Excel spreadsheets (.xlsx) via openpyxl
  - PowerPoint presentations (.pptx) via python-pptx  (with transitions + charts)
  - PDF reports (.pdf)       via reportlab
  - Data analysis charts     via pandas + matplotlib

All outputs are saved to the 'outputs/' folder by default.
Content for presentations/reports can be fetched from the internet.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from tools.project_paths import project_path

logger = logging.getLogger(__name__)

OUTPUT_DIR = project_path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_filename(name: str, ext: str) -> str:
    """Turn any string into a safe filename with the given extension."""
    safe = re.sub(r'[^a-zA-Z0-9_\- ]', '', name).strip().replace(' ', '_')[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{ts}.{ext}" if safe else f"document_{ts}.{ext}"


def _output_path(filename: str) -> str:
    return str(OUTPUT_DIR / filename)


# ─── Web content fetch ────────────────────────────────────────────────────────

def fetch_web_content(query: str, max_chars: int = 8000) -> str:
    """Fetch summarised content from the internet for a given query."""
    try:
        import urllib.request
        import urllib.parse
        encoded = urllib.parse.quote_plus(query)
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&srlimit=3"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("query", {}).get("search", [])
        content_parts = []

        for item in results[:3]:
            title = item.get("title", "")
            snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
            content_parts.append(f"=== {title} ===\n{snippet}")

            # Fetch full Wikipedia article text
            page_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(title)}&format=json"
            try:
                with urllib.request.urlopen(page_url, timeout=10) as page_resp:
                    page_data = json.loads(page_resp.read().decode())
                    pages = page_data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        extract = page.get("extract", "")[:2000]
                        if extract:
                            content_parts.append(extract)
            except Exception:
                pass

        combined = "\n\n".join(content_parts)
        return combined[:max_chars] if combined else f"Information about {query} from research."

    except Exception as exc:
        logger.warning("Web fetch failed: %s", exc)
        return f"Content about {query}."


# ─── Theme Engine ────────────────────────────────────────────────────────────

_THEME_PRESETS = {
    "technology": {
        "primary": "#0D47A1", "secondary": "#1565C0", "accent": "#00BCD4",
        "bg_dark": "#0A1929", "bg_light": "#F5F7FA", "text_dark": "#1A1A2E", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "business": {
        "primary": "#1A237E", "secondary": "#283593", "accent": "#FF6F00",
        "bg_dark": "#0D1B2A", "bg_light": "#FAFAFA", "text_dark": "#212121", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "nature": {
        "primary": "#1B5E20", "secondary": "#2E7D32", "accent": "#FFC107",
        "bg_dark": "#0D2818", "bg_light": "#F1F8E9", "text_dark": "#1B2E1A", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "health": {
        "primary": "#00695C", "secondary": "#00897B", "accent": "#E91E63",
        "bg_dark": "#002A22", "bg_light": "#E0F2F1", "text_dark": "#1A2E2A", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "creative": {
        "primary": "#6A1B9A", "secondary": "#8E24AA", "accent": "#FF4081",
        "bg_dark": "#1A0A2E", "bg_light": "#F3E5F5", "text_dark": "#1A1A2E", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "education": {
        "primary": "#1565C0", "secondary": "#1976D2", "accent": "#FF9800",
        "bg_dark": "#0A1929", "bg_light": "#E3F2FD", "text_dark": "#1A1A2E", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "finance": {
        "primary": "#004D40", "secondary": "#00695C", "accent": "#FFD600",
        "bg_dark": "#001A14", "bg_light": "#E0F2F1", "text_dark": "#1A2E2A", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
    "minimal": {
        "primary": "#212121", "secondary": "#424242", "accent": "#2196F3",
        "bg_dark": "#121212", "bg_light": "#FAFAFA", "text_dark": "#212121", "text_light": "#FFFFFF",
        "font_heading": "Segoe UI", "font_body": "Segoe UI",
    },
}

_THEME_KEYWORDS = {
    "technology": ["tech", "software", "ai", "artificial intelligence", "machine learning",
                   "data", "computer", "digital", "cyber", "programming", "algorithm",
                   "robot", "automation", "cloud", "iot", "blockchain", "neural", "api"],
    "business": ["business", "corporate", "strategy", "management", "leadership", "startup",
                 "enterprise", "market", "revenue", "growth", "company", "organization", "plan"],
    "nature": ["nature", "environment", "climate", "sustainability", "green", "eco",
               "renewable", "planet", "wildlife", "ocean", "forest", "earth", "energy"],
    "health": ["health", "medical", "healthcare", "wellness", "fitness", "hospital",
               "disease", "pharma", "mental health", "nutrition", "biology", "patient"],
    "creative": ["design", "art", "creative", "brand", "fashion", "photography", "music",
                 "film", "media", "entertainment", "culture", "visual", "ux", "ui"],
    "education": ["education", "learning", "school", "university", "student", "teaching",
                  "course", "academic", "training", "research", "science", "study"],
    "finance": ["finance", "banking", "investment", "stock", "trading", "economics",
                "budget", "accounting", "wealth", "insurance", "tax", "crypto", "money"],
}


def _detect_theme(topic: str, custom: dict = None) -> dict:
    default = dict(_THEME_PRESETS["minimal"])
    if custom:
        style = custom.get("style", "")
        if style in _THEME_PRESETS:
            base = dict(_THEME_PRESETS[style])
        else:
            base = dict(default)
        base.update({k: v for k, v in custom.items() if v and k != "style"})
        return base
    lower = topic.lower()
    best, best_score = "minimal", 0
    for cat, kws in _THEME_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in lower)
        if score > best_score:
            best_score = score
            best = cat
    return dict(_THEME_PRESETS[best])


# ─── Word Documents (.docx) ───────────────────────────────────────────────────

def create_word_document(
    title: str,
    content: str,
    author: str = "TOM Agent",
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a professional Word document with proper formatting."""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        return {"status": "error", "message": "python-docx not installed. Run: pip install python-docx"}

    doc = Document()

    # ── Document properties ──
    core_props = doc.core_properties
    core_props.author = author
    core_props.title = title
    core_props.created = datetime.now()

    # ── Page margins ──
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    T = _detect_theme(title)

    # ── Title ──
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.runs[0]
    title_run.font.color.rgb = RGBColor(*_hex_to_rgb(T["primary"]))
    title_run.font.name = T["font_heading"]

    # ── Date line ──
    date_para = doc.add_paragraph(datetime.now().strftime("%B %d, %Y"))
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para.runs[0].font.size = Pt(11)
    date_para.runs[0].font.color.rgb = RGBColor(0x60, 0x60, 0x60)

    doc.add_paragraph("")

    # ── Parse content into sections ──
    lines = content.strip().split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph("")
            continue

        # Heading detection
        if stripped.startswith('# '):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith('## '):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith('### '):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith(('- ', '* ', '• ')):
            p = doc.add_paragraph(stripped[2:], style='List Bullet')
            p.paragraph_format.left_indent = Inches(0.25)
        elif re.match(r'^\d+\.\s', stripped):
            text = re.sub(r'^\d+\.\s', '', stripped)
            doc.add_paragraph(text, style='List Number')
        else:
            p = doc.add_paragraph(stripped)
            p.paragraph_format.space_after = Pt(6)
            # Make bold text work
            if '**' in stripped:
                p.clear()
                parts = re.split(r'\*\*(.+?)\*\*', stripped)
                run_obj = None
                for i, part in enumerate(parts):
                    run_obj = p.add_run(part)
                    if i % 2 == 1:
                        run_obj.bold = True

    # ── Footer with page numbers ──
    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer_para.add_run(f"Generated by TOM Agent  ·  {datetime.now().strftime('%Y-%m-%d')}  ·  Page ")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    page_num = OxmlElement('w:fldSimple')
    page_num.set(qn('w:instr'), 'PAGE')
    run2 = OxmlElement('w:r')
    run2_text = OxmlElement('w:t')
    run2_text.text = "1"
    run2.append(run2_text)
    page_num.append(run2)
    footer_para._element.append(page_num)

    fname = filename or _safe_filename(title, "docx")
    fpath = _output_path(fname)
    doc.save(fpath)
    return {"status": "success", "path": fpath, "message": f"Word document saved: {fpath}"}


# ─── Excel Spreadsheets (.xlsx) ───────────────────────────────────────────────

def create_excel_spreadsheet(
    title: str,
    data: Optional[List[Dict[str, Any]]] = None,
    content_description: str = "",
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a professional Excel spreadsheet with formatting and formulas."""
    try:
        import openpyxl
        from openpyxl.styles import (
            Font, Fill, PatternFill, Alignment, Border, Side, GradientFill
        )
        from openpyxl.utils import get_column_letter
        from openpyxl.chart import BarChart, Reference
    except ImportError:
        return {"status": "error", "message": "openpyxl not installed. Run: pip install openpyxl"}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:30]

    # ── Theme colors (auto-detected from title) ──
    T = _detect_theme(title)
    pri = T["primary"].lstrip("#")
    bg = T["bg_light"].lstrip("#")
    header_fill = PatternFill("solid", fgColor=pri)
    alt_fill = PatternFill("solid", fgColor=bg)
    total_fill = PatternFill("solid", fgColor=bg)
    header_font = Font(name=T["font_body"], bold=True, color="FFFFFF", size=11)
    title_font = Font(name=T["font_heading"], bold=True, size=16, color=pri)
    body_font = Font(name=T["font_body"], size=10)
    total_font = Font(name=T["font_body"], bold=True, size=10, color=pri)

    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    # ── Title row ──
    ws.merge_cells("A1:F1")
    ws["A1"] = title
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    ws.merge_cells("A2:F2")
    ws["A2"] = f"Generated by TOM Agent  |  {datetime.now().strftime('%B %d, %Y')}"
    ws["A2"].font = Font(name="Calibri", italic=True, size=10, color="666666")
    ws["A2"].alignment = Alignment(horizontal="center")

    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 8  # spacer

    # ── Data ──
    if data:
        headers = list(data[0].keys())
        header_row = 4

        # Write headers
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=header_row, column=col_idx, value=header.replace('_', ' ').title())
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws.row_dimensions[header_row].height = 22

        # Write data rows
        for row_idx, row_data in enumerate(data, header_row + 1):
            fill = alt_fill if (row_idx - header_row) % 2 == 0 else PatternFill()
            for col_idx, header in enumerate(headers, 1):
                val = row_data.get(header, "")
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = body_font
                cell.fill = fill
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")
                if isinstance(val, (int, float)):
                    cell.alignment = Alignment(horizontal="right", vertical="center")

        # Totals row for numeric columns
        total_row = header_row + len(data) + 1
        ws.cell(row=total_row, column=1, value="TOTAL").font = total_font
        ws.cell(row=total_row, column=1).fill = total_fill
        ws.cell(row=total_row, column=1).border = thin_border

        for col_idx, header in enumerate(headers[1:], 2):
            vals = [row.get(header) for row in data]
            if all(isinstance(v, (int, float)) for v in vals if v is not None):
                formula_col = get_column_letter(col_idx)
                formula = f"=SUM({formula_col}{header_row+1}:{formula_col}{header_row+len(data)})"
                cell = ws.cell(row=total_row, column=col_idx, value=formula)
                cell.font = total_font
                cell.fill = total_fill
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="right", vertical="center")

        # Auto column width
        for col_idx in range(1, len(headers) + 1):
            max_len = 0
            col_letter = get_column_letter(col_idx)
            for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 40)

        # ── Bar chart ──
        try:
            numeric_cols = [i+1 for i, h in enumerate(headers[1:], 0) if all(
                isinstance(row.get(headers[i+1]), (int, float)) for row in data if row.get(headers[i+1]) is not None
            )]
            if numeric_cols:
                chart = BarChart()
                chart.type = "col"
                chart.style = 10
                chart.title = f"{title} — Overview"
                chart.y_axis.title = "Value"
                chart.x_axis.title = headers[0].title()
                chart.width = 18
                chart.height = 12

                data_ref = Reference(ws, min_col=numeric_cols[0]+1, max_col=numeric_cols[0]+1,
                                     min_row=header_row, max_row=header_row + len(data))
                cats = Reference(ws, min_col=1, min_row=header_row+1, max_row=header_row+len(data))
                chart.add_data(data_ref, titles_from_data=True)
                chart.set_categories(cats)

                chart_sheet = wb.create_sheet("Chart")
                chart_sheet.add_chart(chart, "B2")
        except Exception:
            pass

    else:
        # Generic template if no data provided
        ws.cell(row=4, column=1, value=f"Topic: {content_description or title}")
        ws.cell(row=4, column=1).font = Font(bold=True, size=11)
        for i, header in enumerate(["Item", "Description", "Value", "Status", "Notes"], 1):
            cell = ws.cell(row=5, column=i, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions[get_column_letter(i)].width = 18
        for row in range(6, 16):
            for col in range(1, 6):
                ws.cell(row=row, column=col).border = thin_border

    fname = filename or _safe_filename(title, "xlsx")
    fpath = _output_path(fname)
    wb.save(fpath)
    return {"status": "success", "path": fpath, "message": f"Excel spreadsheet saved: {fpath}"}


# ─── PowerPoint Presentations (.pptx) ────────────────────────────────────────

def create_presentation(
    title: str,
    slides_content: Optional[List[Dict[str, Any]]] = None,
    search_topic: Optional[str] = None,
    filename: Optional[str] = None,
    llm_content: Optional[str] = None,
    theme: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt, Emu
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        from lxml import etree
    except ImportError:
        return {"status": "error", "message": "python-pptx not installed. Run: pip install python-pptx lxml"}

    T = _detect_theme(title + " " + (search_topic or ""), theme)

    web_content = ""
    if search_topic:
        web_content = fetch_web_content(search_topic)

    if not slides_content:
        raw = llm_content or web_content or f"Professional presentation about {title}."
        slides_content = _parse_slides_from_text(title, raw)

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ── TITLE SLIDE ──────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    _set_gradient_bg(slide, T["bg_dark"], T["primary"])

    _add_rounded_rect(slide, Inches(0), Inches(6.8), Inches(13.33), Inches(0.7),
                      T["accent"], alpha=40)

    _add_text_box(slide, title, Inches(1), Inches(2.2), Inches(11.33), Inches(1.6),
                  font_size=44, color=T["text_light"], bold=True,
                  align=PP_ALIGN.LEFT, font_name=T["font_heading"])

    _add_rect(slide, Inches(1), Inches(3.9), Inches(3), Inches(0.05), T["accent"])

    sub_text = f"Prepared by TOM Agent  ·  {datetime.now().strftime('%B %d, %Y')}"
    _add_text_box(slide, sub_text, Inches(1), Inches(4.2), Inches(8), Inches(0.6),
                  font_size=18, color=T["accent"], font_name=T["font_body"])

    _add_transition(slide, "fade")

    # ── CONTENT SLIDES ───────────────────────────────────────────────────
    transitions = ["fade", "push", "wipe", "cover", "split", "reveal", "randomBars", "dissolve"]

    for i, sd in enumerate(slides_content):
        slide_title = sd.get("title", f"Section {i+1}")
        bullets = sd.get("bullets", sd.get("content", []))
        notes = sd.get("notes", sd.get("subtitle", ""))
        layout = sd.get("layout", "content")
        table_data = sd.get("table_data")
        chart_data = sd.get("chart_data")

        slide = prs.slides.add_slide(blank_layout)

        if layout == "section_header":
            _set_gradient_bg(slide, T["primary"], T["secondary"])
            _add_text_box(slide, slide_title, Inches(1.2), Inches(2.5), Inches(11), Inches(1.4),
                          font_size=38, color=T["text_light"], bold=True,
                          font_name=T["font_heading"], align=PP_ALIGN.LEFT)
            _add_rect(slide, Inches(1.2), Inches(4.0), Inches(2.5), Inches(0.05), T["accent"])
            if bullets:
                _add_text_box(slide, bullets[0] if isinstance(bullets[0], str) else str(bullets[0]),
                              Inches(1.2), Inches(4.3), Inches(9), Inches(0.8),
                              font_size=18, color=T["text_light"], font_name=T["font_body"])
        else:
            _ppt_set_solid_bg(slide, T["bg_light"])

            _add_rect(slide, Inches(0), Inches(0), Inches(0.35), Inches(7.5), T["primary"])

            _add_rounded_rect(slide, Inches(0), Inches(0), Inches(13.33), Inches(0.06),
                              T["accent"], alpha=60)

            _add_text_box(slide, slide_title, Inches(0.7), Inches(0.3), Inches(11.5), Inches(0.9),
                          font_size=28, color=T["primary"], bold=True,
                          font_name=T["font_heading"], align=PP_ALIGN.LEFT)

            _add_rect(slide, Inches(0.7), Inches(1.2), Inches(2), Inches(0.04), T["accent"])

            content_top = Inches(1.5)
            content_left = Inches(0.7)
            content_width = Inches(11.8)

            if table_data and isinstance(table_data, dict):
                _add_ppt_table(slide, table_data, content_left, content_top,
                               content_width, Inches(4.5), T)
            elif chart_data and isinstance(chart_data, dict):
                _add_ppt_chart(slide, chart_data, content_left, content_top,
                               content_width, Inches(5), T)
            elif layout == "two_column" and len(bullets) >= 2:
                mid = len(bullets) // 2
                col_w = Inches(5.5)
                _add_bullet_box(slide, bullets[:mid], content_left, content_top,
                                col_w, Inches(5), T)
                _add_bullet_box(slide, bullets[mid:], Inches(6.8), content_top,
                                col_w, Inches(5), T)
            else:
                _add_bullet_box(slide, bullets, content_left, content_top,
                                content_width, Inches(5.2), T)

            _add_rect(slide, Inches(0), Inches(7.1), Inches(13.33), Inches(0.4), T["primary"])
            _add_text_box(slide, f"{i + 2}", Inches(0.5), Inches(7.12), Inches(1), Inches(0.35),
                          font_size=10, color=T["text_light"], font_name=T["font_body"])
            _add_text_box(slide, title, Inches(4), Inches(7.12), Inches(5.33), Inches(0.35),
                          font_size=10, color=T["text_light"], align=PP_ALIGN.CENTER,
                          font_name=T["font_body"])

        if notes:
            slide.notes_slide.notes_text_frame.text = notes

        _add_transition(slide, transitions[i % len(transitions)])

    # ── CLOSING SLIDE ────────────────────────────────────────────────────
    slide = prs.slides.add_slide(blank_layout)
    _set_gradient_bg(slide, T["primary"], T["bg_dark"])

    _add_text_box(slide, "Thank You", Inches(1), Inches(2.4), Inches(11.33), Inches(1.4),
                  font_size=48, color=T["text_light"], bold=True,
                  font_name=T["font_heading"], align=PP_ALIGN.CENTER)

    _add_rect(slide, Inches(5.5), Inches(3.9), Inches(2.33), Inches(0.05), T["accent"])

    _add_text_box(slide, f"Generated by TOM  ·  {datetime.now().strftime('%B %d, %Y')}",
                  Inches(2), Inches(4.3), Inches(9.33), Inches(0.6),
                  font_size=16, color=T["accent"], font_name=T["font_body"],
                  align=PP_ALIGN.CENTER)
    _add_transition(slide, "fade")

    fname = filename or _safe_filename(title, "pptx")
    fpath = _output_path(fname)
    prs.save(fpath)
    return {"status": "success", "path": fpath,
            "message": f"Presentation saved: {fpath} ({len(slides_content) + 2} slides)"}


# ─── Presentation Helpers ────────────────────────────────────────────────────

def _parse_slides_from_text(title: str, text: str) -> List[Dict[str, Any]]:
    slides = []
    current_title = None
    current_bullets: List[str] = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(('#', '==')):
            if current_title and current_bullets:
                slides.append({"title": current_title, "bullets": current_bullets, "notes": ""})
            current_title = stripped.lstrip('#= ').strip()
            current_bullets = []
        elif stripped.startswith(('-', '*', '•', '·')):
            bullet = stripped.lstrip('-*•· ').strip()
            if bullet and len(bullet) > 3:
                current_bullets.append(bullet)
        elif current_title and len(stripped) > 20:
            current_bullets.append(textwrap.shorten(stripped, width=120, placeholder="..."))
    if current_title and current_bullets:
        slides.append({"title": current_title, "bullets": current_bullets, "notes": ""})
    if not slides:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        section_titles = ["Introduction", "Key Facts", "Analysis",
                          "Key Insights", "Impact & Implications", "Recommendations"]
        for i, para in enumerate(paragraphs[:6]):
            bullets = [textwrap.shorten(s.strip(), 110, placeholder="...")
                       for s in para.split('. ') if len(s.strip()) > 15][:5]
            slides.append({"title": section_titles[i] if i < len(section_titles) else f"Section {i+1}",
                           "bullets": bullets or [para[:120]], "notes": para})
    return slides or [{"title": "Overview", "bullets": [f"Presentation about {title}"], "notes": ""}]


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _ppt_set_solid_bg(slide, hex_color: str):
    from pptx.dml.color import RGBColor
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(*_hex_to_rgb(hex_color))


def _set_gradient_bg(slide, color1: str, color2: str, angle: int = 270):
    try:
        from lxml import etree
        from pptx.oxml.ns import qn
        bg_elem = slide.background._element
        bgPr = bg_elem.find(qn('p:bgPr'))
        if bgPr is None:
            bgPr = etree.SubElement(bg_elem, qn('p:bgPr'))
        for child in list(bgPr):
            bgPr.remove(child)
        gf = etree.SubElement(bgPr, qn('a:gradFill'))
        gf.set('flip', 'none')
        gf.set('rotWithShape', '0')
        gsLst = etree.SubElement(gf, qn('a:gsLst'))
        gs1 = etree.SubElement(gsLst, qn('a:gs'))
        gs1.set('pos', '0')
        c1 = etree.SubElement(gs1, qn('a:srgbClr'))
        c1.set('val', color1.lstrip('#'))
        gs2 = etree.SubElement(gsLst, qn('a:gs'))
        gs2.set('pos', '100000')
        c2 = etree.SubElement(gs2, qn('a:srgbClr'))
        c2.set('val', color2.lstrip('#'))
        lin = etree.SubElement(gf, qn('a:lin'))
        lin.set('ang', str(angle * 60000))
        lin.set('scaled', '1')
        etree.SubElement(bgPr, qn('a:effectLst'))
    except Exception:
        _ppt_set_solid_bg(slide, color1)


def _add_rect(slide, left, top, width, height, hex_color: str):
    from pptx.dml.color import RGBColor
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*_hex_to_rgb(hex_color))
    shape.line.fill.background()
    return shape


def _add_rounded_rect(slide, left, top, width, height, hex_color: str, alpha: int = 100):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(*_hex_to_rgb(hex_color))
    if alpha < 100:
        try:
            from lxml import etree
            from pptx.oxml.ns import qn
            srgb = shape.fill._fill.find(qn('a:solidFill')).find(qn('a:srgbClr'))
            if srgb is not None:
                a_elem = etree.SubElement(srgb, qn('a:alpha'))
                a_elem.set('val', str(alpha * 1000))
        except Exception:
            pass
    shape.line.fill.background()
    return shape


def _add_text_box(slide, text, left, top, width, height, font_size=12,
                  color="000000", bold=False, align=None, font_name=None):
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = str(text)
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = RGBColor(*_hex_to_rgb(color))
    if font_name:
        p.font.name = font_name
    if align:
        p.alignment = align
    return txBox


def _add_bullet_box(slide, bullets, left, top, width, height, T):
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for j, bullet in enumerate(bullets[:8]):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.text = str(bullet)
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(*_hex_to_rgb(T["text_dark"]))
        p.font.name = T["font_body"]
        p.space_before = Pt(6)
        p.space_after = Pt(6)
        p.level = 0


def _add_ppt_table(slide, table_data, left, top, width, height, T):
    from pptx.util import Pt, Inches
    from pptx.dml.color import RGBColor
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", table_data.get("data", []))
    if not headers or not rows:
        return
    n_rows = min(len(rows) + 1, 12)
    n_cols = len(headers)
    tbl_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    tbl = tbl_shape.table
    for ci, h in enumerate(headers):
        cell = tbl.cell(0, ci)
        cell.text = str(h)
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            p.font.name = T["font_body"]
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(*_hex_to_rgb(T["primary"]))
    for ri, row in enumerate(rows[:n_rows - 1]):
        for ci, val in enumerate(row[:n_cols]):
            cell = tbl.cell(ri + 1, ci)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = RGBColor(*_hex_to_rgb(T["text_dark"]))
                p.font.name = T["font_body"]
            if ri % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(*_hex_to_rgb(T["bg_light"]))


def _add_ppt_chart(slide, chart_data, left, top, width, height, T):
    try:
        from pptx.chart.data import CategoryChartData
        from pptx.enum.chart import XL_CHART_TYPE
        from pptx.util import Pt
        from pptx.dml.color import RGBColor
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        chart_type_str = chart_data.get("type", "bar").lower()
        chart_title = chart_data.get("title", "")
        type_map = {
            "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
            "line": XL_CHART_TYPE.LINE_MARKERS,
            "pie": XL_CHART_TYPE.PIE,
            "area": XL_CHART_TYPE.AREA,
        }
        xl_type = type_map.get(chart_type_str, XL_CHART_TYPE.COLUMN_CLUSTERED)
        cd = CategoryChartData()
        cd.categories = labels
        cd.add_series("Data", values)
        chart_shape = slide.shapes.add_chart(xl_type, left, top, width, height, cd)
        chart = chart_shape.chart
        chart.has_legend = False
        if chart_title:
            chart.has_title = True
            chart.chart_title.text_frame.text = chart_title
    except Exception:
        _add_text_box(slide, "[Chart could not be generated]", left, top, width, height,
                      font_size=14, color=T["text_dark"])


def _add_transition(slide, transition_type: str = "fade"):
    try:
        from lxml import etree
        ns = 'http://schemas.openxmlformats.org/presentationml/2006/main'
        ns14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'
        tr = etree.SubElement(slide._element, f'{{{ns}}}transition')
        tr.set('spd', 'med')
        tr.set('advTm', '0')
        effect_map = {
            "fade": lambda: etree.SubElement(tr, f'{{{ns}}}fade'),
            "wipe": lambda: etree.SubElement(tr, f'{{{ns}}}wipe').set('dir', 'r') or None,
            "push": lambda: etree.SubElement(tr, f'{{{ns}}}push').set('dir', 'r') or None,
            "cover": lambda: etree.SubElement(tr, f'{{{ns}}}cover').set('dir', 'r') or None,
            "split": lambda: etree.SubElement(tr, f'{{{ns}}}split'),
            "reveal": lambda: etree.SubElement(tr, f'{{{ns14}}}reveal'),
            "randomBars": lambda: etree.SubElement(tr, f'{{{ns}}}randomBar'),
            "dissolve": lambda: etree.SubElement(tr, f'{{{ns}}}dissolve'),
        }
        fn = effect_map.get(transition_type)
        if fn:
            fn()
        else:
            etree.SubElement(tr, f'{{{ns}}}fade')
    except Exception:
        pass


# ─── PDF Reports (.pdf) ───────────────────────────────────────────────────────

def create_pdf_report(
    title: str,
    content: str,
    author: str = "TOM Agent",
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a professional PDF report using reportlab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
            Table, TableStyle, PageBreak, KeepTogether,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.pdfbase import pdfmetrics
    except ImportError:
        return {"status": "error", "message": "reportlab not installed. Run: pip install reportlab"}

    fname = filename or _safe_filename(title, "pdf")
    fpath = _output_path(fname)

    T = _detect_theme(title)
    DARK_BLUE = colors.HexColor(T["primary"])
    MID_BLUE = colors.HexColor(T["secondary"])
    LIGHT_BLUE = colors.HexColor(T["bg_light"])
    GREY = colors.HexColor("#455A64")
    LIGHT_GREY = colors.HexColor("#F5F5F5")

    doc = SimpleDocTemplate(
        fpath, pagesize=A4,
        rightMargin=2.0*cm, leftMargin=2.0*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
        title=title, author=author,
    )

    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle("H1", parent=styles["Heading1"],
                               fontSize=22, textColor=DARK_BLUE,
                               spaceAfter=12, spaceBefore=6, fontName="Helvetica-Bold")
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                               fontSize=16, textColor=MID_BLUE,
                               spaceAfter=8, spaceBefore=12, fontName="Helvetica-Bold")
    style_h3 = ParagraphStyle("H3", parent=styles["Heading3"],
                               fontSize=13, textColor=GREY,
                               spaceAfter=6, spaceBefore=8, fontName="Helvetica-Bold")
    style_body = ParagraphStyle("Body", parent=styles["Normal"],
                                fontSize=10.5, leading=15, textColor=colors.black,
                                spaceAfter=8, alignment=TA_JUSTIFY, fontName="Helvetica")
    style_bullet = ParagraphStyle("Bullet", parent=styles["Normal"],
                                  fontSize=10.5, leading=15, leftIndent=20,
                                  bulletIndent=8, textColor=colors.black,
                                  spaceAfter=4, fontName="Helvetica")
    style_title = ParagraphStyle("Title", parent=styles["Title"],
                                 fontSize=30, textColor=colors.white,
                                 alignment=TA_CENTER, fontName="Helvetica-Bold",
                                 spaceAfter=6)
    style_subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"],
                                    fontSize=13, textColor=colors.HexColor("#BBDEFB"),
                                    alignment=TA_CENTER, fontName="Helvetica")

    story = []

    # ── Cover block ──
    cover_data = [[Paragraph(title, style_title)],
                  [Paragraph(f"Author: {author}  |  Date: {datetime.now().strftime('%B %d, %Y')}", style_subtitle)]]
    cover_table = Table(cover_data, colWidths=[doc.width])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [DARK_BLUE, MID_BLUE]),
        ("TOPPADDING", (0, 0), (-1, -1), 28),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 28),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 20))

    # ── Parse content ──
    lines = content.strip().split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 6))
            continue

        if stripped.startswith('# '):
            story.append(HRFlowable(width="100%", color=DARK_BLUE, thickness=1.5, spaceAfter=4))
            story.append(Paragraph(stripped[2:], style_h1))
        elif stripped.startswith('## '):
            story.append(Paragraph(stripped[3:], style_h2))
        elif stripped.startswith('### '):
            story.append(Paragraph(stripped[4:], style_h3))
        elif stripped.startswith(('- ', '* ', '• ')):
            story.append(Paragraph(f"• {stripped[2:]}", style_bullet))
        elif re.match(r'^\d+\.\s', stripped):
            text = re.sub(r'^\d+\.\s', '', stripped)
            story.append(Paragraph(f"• {text}", style_bullet))
        else:
            # Handle **bold** markdown
            html_line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
            story.append(Paragraph(html_line, style_body))

    def _add_page_number(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#999999"))
        page_num = canvas.getPageNumber()
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm,
                                 f"{title}  ·  Page {page_num}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return {"status": "success", "path": fpath, "message": f"PDF report saved: {fpath}"}


# ─── Data Analysis ────────────────────────────────────────────────────────────

def analyze_data_and_create_charts(
    data_source: str,
    analysis_request: str,
    output_prefix: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load data from CSV/Excel, run analysis, and create professional charts.
    Returns paths to generated chart images and a summary.
    """
    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        from matplotlib.gridspec import GridSpec
        import numpy as np
    except ImportError:
        return {"status": "error",
                "message": "pandas/matplotlib not installed. Run: pip install pandas matplotlib numpy"}

    # ── Load data ──
    if not os.path.exists(data_source):
        return {"status": "error", "message": f"Data file not found: {data_source}"}

    try:
        if data_source.endswith('.csv'):
            df = pd.read_csv(data_source)
        elif data_source.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(data_source)
        elif data_source.endswith('.json'):
            df = pd.read_json(data_source)
        else:
            return {"status": "error", "message": f"Unsupported data format: {data_source}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load data: {e}"}

    prefix = output_prefix or _safe_filename(os.path.basename(data_source), "chart").replace(".chart", "")
    chart_paths = []
    summary_lines = [
        f"## Data Analysis Report — {os.path.basename(data_source)}",
        f"**Rows:** {len(df)}  |  **Columns:** {len(df.columns)}",
        f"**Columns:** {', '.join(df.columns.tolist())}",
    ]

    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    # ── Chart 1: Overview / Distribution ──
    if numeric_cols:
        fig = plt.figure(figsize=(16, 10), facecolor='white')
        fig.suptitle(f"Data Analysis — {os.path.basename(data_source)}", fontsize=18,
                     fontweight='bold', color='#1A237E', y=0.98)

        n_plots = min(len(numeric_cols), 4)
        gs = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

        color_cycle = ['#1565C0', '#2E7D32', '#6A1B9A', '#BF360C']

        for idx, col in enumerate(numeric_cols[:4]):
            ax = fig.add_subplot(gs[idx // 2, idx % 2])
            data_clean = df[col].dropna()

            if len(data_clean) < 20:
                ax.bar(range(len(data_clean)), data_clean, color=color_cycle[idx], alpha=0.85, edgecolor='white')
                ax.set_title(col, fontsize=12, fontweight='bold', color='#1A237E', pad=8)
                ax.set_xlabel("Index", fontsize=9)
            else:
                ax.hist(data_clean, bins=20, color=color_cycle[idx], alpha=0.8, edgecolor='white')
                ax.set_title(f"{col} — Distribution", fontsize=12, fontweight='bold', color='#1A237E', pad=8)
                ax.set_xlabel(col, fontsize=9)

            ax.set_ylabel("Count / Value", fontsize=9)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(labelsize=8)

            # Add mean line
            mean_val = data_clean.mean()
            ax.axvline(mean_val, color='red', linestyle='--', alpha=0.7, linewidth=1.2,
                       label=f"Mean: {mean_val:.1f}")
            ax.legend(fontsize=8)

        chart1 = _output_path(f"{prefix}_distribution.png")
        plt.savefig(chart1, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_paths.append(chart1)

    # ── Chart 2: Correlation heatmap ──
    if len(numeric_cols) >= 2:
        fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')
        corr = df[numeric_cols].corr()
        import numpy as np
        mask = np.triu(np.ones_like(corr, dtype=bool))
        cmap = plt.cm.RdYlBu_r
        im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1, aspect='auto')
        ax.set_xticks(range(len(numeric_cols)))
        ax.set_yticks(range(len(numeric_cols)))
        ax.set_xticklabels(numeric_cols, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(numeric_cols, fontsize=9)
        for i in range(len(numeric_cols)):
            for j in range(len(numeric_cols)):
                text = ax.text(j, i, f'{corr.iloc[i, j]:.2f}',
                               ha='center', va='center', fontsize=8,
                               color='black' if abs(corr.iloc[i, j]) < 0.7 else 'white')
        plt.colorbar(im, ax=ax, shrink=0.8)
        ax.set_title('Correlation Matrix', fontsize=14, fontweight='bold', color='#1A237E', pad=12)
        fig.suptitle('How variables relate to each other', fontsize=10, color='grey', y=0.02)
        chart2 = _output_path(f"{prefix}_correlation.png")
        plt.savefig(chart2, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_paths.append(chart2)

    # ── Chart 3: Category breakdown ──
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor='white')
        fig.suptitle(f"{cat_col} Breakdown", fontsize=14, fontweight='bold', color='#1A237E')

        grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(10)
        colors_list = plt.cm.Set2(range(len(grouped)))
        ax1.barh(grouped.index, grouped.values, color=colors_list, edgecolor='white', height=0.7)
        ax1.set_xlabel(num_col, fontsize=10)
        ax1.set_title(f"Top {cat_col}s by {num_col}", fontsize=11, color='#1A237E')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)

        pie_grouped = df.groupby(cat_col)[num_col].sum().head(8)
        explode = [0.05] * len(pie_grouped)
        ax2.pie(pie_grouped.values, labels=pie_grouped.index, autopct='%1.1f%%',
                colors=plt.cm.Set3(range(len(pie_grouped))), explode=explode,
                startangle=140, pctdistance=0.85)
        ax2.set_title(f"Share by {cat_col}", fontsize=11, color='#1A237E')

        chart3 = _output_path(f"{prefix}_categories.png")
        plt.savefig(chart3, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        chart_paths.append(chart3)

    # ── Statistical summary ──
    if numeric_cols:
        desc = df[numeric_cols].describe().round(2)
        summary_lines.append("\n### Statistical Summary")
        for col in numeric_cols:
            summary_lines.append(
                f"- **{col}**: mean={desc[col]['mean']:.2f}, "
                f"min={desc[col]['min']:.2f}, max={desc[col]['max']:.2f}, "
                f"std={desc[col]['std']:.2f}"
            )

    # ── Insights ──
    summary_lines.append("\n### Key Insights")
    if numeric_cols:
        for col in numeric_cols[:3]:
            vals = df[col].dropna()
            if len(vals) > 1:
                pct_change = ((vals.iloc[-1] - vals.iloc[0]) / abs(vals.iloc[0])) * 100 if vals.iloc[0] != 0 else 0
                trend = "upward" if pct_change > 0 else "downward"
                summary_lines.append(f"- **{col}**: {trend} trend ({pct_change:+.1f}% overall change)")

    return {
        "status": "success",
        "summary": "\n".join(summary_lines),
        "chart_paths": chart_paths,
        "message": f"Analysis complete. {len(chart_paths)} charts generated.",
    }


# ─── Quick code file creator ─────────────────────────────────────────────────

def create_code_file(
    filename: str,
    description: str = "",
    content: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a code file with the appropriate scaffold based on its extension."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'txt'
    fpath = _output_path(filename)

    if content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "path": fpath, "message": f"File created: {fpath}"}

    templates = {
        "py": f'''#!/usr/bin/env python3
"""
{description or filename}
Generated by TOM Agent — {datetime.now().strftime('%Y-%m-%d')}
"""

import asyncio


async def main():
    print("Hello from {filename}")
    # TODO: implement your logic here


if __name__ == "__main__":
    asyncio.run(main())
''',
        "html": f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{description or filename.replace('.html', '')}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>{description or 'Welcome'}</h1>
    </header>
    <main>
        <p>Generated by TOM Agent.</p>
    </main>
    <footer>
        <p>&copy; {datetime.now().year}</p>
    </footer>
    <script src="script.js"></script>
</body>
</html>''',
        "css": f'''/* {description or filename} — Generated by TOM Agent */

*, *::before, *::after {{
  box-sizing: border-box;
}}

body {{
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', Arial, sans-serif;
  background: #f9fafb;
  color: #1a1a2e;
  line-height: 1.6;
}}

header {{
  background: #1A237E;
  color: white;
  padding: 1.5rem 2rem;
}}

main {{
  max-width: 960px;
  margin: 2rem auto;
  padding: 0 1.5rem;
}}

footer {{
  text-align: center;
  padding: 1rem;
  color: #666;
  border-top: 1px solid #ddd;
}}
''',
        "js": f'''// {description or filename} — Generated by TOM Agent

"use strict";

document.addEventListener("DOMContentLoaded", () => {{
    console.log("TOM Agent script loaded.");
    // TODO: add your logic here
}});
''',
        "json": f'{{\n  "name": "{description or filename}",\n  "version": "1.0.0",\n  "generated_by": "TOM Agent"\n}}',
        "md": f'''# {description or filename}

> Generated by TOM Agent — {datetime.now().strftime('%Y-%m-%d')}

## Overview

TODO: Add content here.

## Usage

```bash
# add usage instructions
```
''',
        "txt": f'''{description or filename}
Generated by TOM Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}

TODO: add content.
''',
    }

    file_content = templates.get(ext, f"# {description or filename}\n# Generated by TOM Agent\n")
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(file_content)

    return {"status": "success", "path": fpath, "message": f"File created: {fpath}"}
