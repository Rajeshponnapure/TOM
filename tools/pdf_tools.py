"""
PDF Report Generator Tool
Generates professional PDF reports from AI news posts.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    """
    Generates professional PDF reports from post data.
    """
    
    def __init__(self, page_size=letter, margin_size=0.5 * inch):
        """
        Initialize PDF generator.
        
        Args:
            page_size: reportlab page size (letter or A4)
            margin_size: Page margin in inches
        """
        self.page_size = page_size
        self.margin_size = margin_size
        self.content_width = self.page_size[0] - (2 * self.margin_size)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=26,
            leading=30,
            textColor=colors.HexColor('#1a1a1e'),
            spaceAfter=8,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportKicker',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#8a6a3f'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=4,
        ))

        self.styles.add(ParagraphStyle(
            name='ReportSubhead',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#4a4a52'),
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=14,
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#1a1a1e'),
            spaceAfter=10,
            spaceBefore=14,
            fontName='Helvetica-Bold',
        ))

        self.styles.add(ParagraphStyle(
            name='PostTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            leading=14,
            textColor=colors.HexColor('#1a1a1e'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor=colors.HexColor('#2c2c34'),
        ))

        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#6f6f78'),
            spaceAfter=4,
            fontName='Helvetica-Oblique'
        ))

        self.styles.add(ParagraphStyle(
            name='ImportanceHigh',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=10,
            textColor=colors.white,
            backColor=colors.HexColor('#7c1d12'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ImportanceMedium',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=10,
            textColor=colors.white,
            backColor=colors.HexColor('#8f5d1f'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='ImportanceLow',
            parent=self.styles['Normal'],
            fontSize=8.5,
            leading=10,
            textColor=colors.white,
            backColor=colors.HexColor('#234a72'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CardLabel',
            parent=self.styles['Normal'],
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor('#8a6a3f'),
            fontName='Helvetica-Bold',
        ))

        self.styles.add(ParagraphStyle(
            name='CardValue',
            parent=self.styles['Normal'],
            fontSize=15,
            leading=17,
            textColor=colors.HexColor('#1a1a1e'),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        ))

        self.styles.add(ParagraphStyle(
            name='CardCaption',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#6f6f78'),
            alignment=TA_CENTER,
        ))
    
    def _get_importance_badge(self, importance: int) -> str:
        """Get visual badge for importance rating."""
        if importance >= 4:
            return "🔴 HIGH"
        elif importance == 3:
            return "🟠 MEDIUM"
        else:
            return "🔵 LOW"
    
    def _get_importance_style(self, importance: int) -> str:
        """Get paragraph style name for importance level."""
        if importance >= 4:
            return 'ImportanceHigh'
        elif importance == 3:
            return 'ImportanceMedium'
        else:
            return 'ImportanceLow'
    
    def _build_header(self, title: str, timestamp: datetime) -> List:
        """Build PDF header section."""
        elements = []
        
        elements.append(Spacer(1, 0.08 * inch))
        elements.append(Paragraph("TOM REPORTING DESK", self.styles['ReportKicker']))
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        
        date_str = timestamp.strftime('%B %d, %Y at %I:%M %p')
        elements.append(Paragraph(
            f"Curated digest generated {date_str}",
            self.styles['ReportSubhead']
        ))
        elements.append(Spacer(1, 0.16 * inch))
        
        return elements

    def _build_kpi_cards(self, posts: List[Dict]) -> List:
        high = sum(1 for p in posts if p.get('importance', 0) >= 4)
        medium = sum(1 for p in posts if p.get('importance', 0) == 3)
        low = sum(1 for p in posts if p.get('importance', 0) < 3)

        cards = [
            [Paragraph("Total Posts", self.styles['CardLabel']), Paragraph(str(len(posts)), self.styles['CardValue']), Paragraph("relevant items surfaced", self.styles['CardCaption'])],
            [Paragraph("High Priority", self.styles['CardLabel']), Paragraph(str(high), self.styles['CardValue']), Paragraph("4-5 star items", self.styles['CardCaption'])],
            [Paragraph("Medium Priority", self.styles['CardLabel']), Paragraph(str(medium), self.styles['CardValue']), Paragraph("3 star items", self.styles['CardCaption'])],
            [Paragraph("Low Priority", self.styles['CardLabel']), Paragraph(str(low), self.styles['CardValue']), Paragraph("1-2 star items", self.styles['CardCaption'])],
        ]

        card_table = Table(cards, colWidths=[self.content_width / 4.0] * 4)
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7f2ea')),
            ('BOX', (0, 0), (-1, -1), 0.9, colors.HexColor('#c9b18a')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d7cab6')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        return [card_table, Spacer(1, 0.16 * inch)]
    
    def _build_summary_section(self, posts: List[Dict]) -> List:
        """Build summary statistics section."""
        elements = []
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        elements.extend(self._build_kpi_cards(posts))
        
        return elements
    
    def _build_posts_section(self, posts: List[Dict], include_importance: bool = True, 
                             include_links: bool = True) -> List:
        """Build posts detail section."""
        elements = []
        
        high_posts = [p for p in posts if p.get('importance', 0) >= 4]
        medium_posts = [p for p in posts if p.get('importance', 0) == 3]
        low_posts = [p for p in posts if p.get('importance', 0) < 3]
        
        post_groups = [
            ("High Priority (4-5 Stars)", high_posts, colors.HexColor('#ffcccc')),
            ("Medium Priority (3 Stars)", medium_posts, colors.HexColor('#ffe6cc')),
            ("Low Priority (1-2 Stars)", low_posts, colors.HexColor('#cce6ff')),
        ]
        
        for section_title, section_posts, header_color in post_groups:
            if not section_posts:
                continue
            
            elements.append(Paragraph(section_title, self.styles['SectionHeader']))
            
            for idx, post in enumerate(section_posts, 1):
                post_elements = self._build_post_entry(post, idx, include_importance, include_links)
                elements.extend(post_elements)
                elements.append(Spacer(1, 0.08 * inch))
            
            elements.append(Spacer(1, 0.1 * inch))
        
        return elements
    
    def _build_post_entry(self, post: Dict, post_number: int, 
                          include_importance: bool, include_links: bool) -> List:
        """Build a single post entry for the report."""
        elements = []
        
        importance = post.get('importance', 0)
        summary = post.get('summary', post.get('text', 'No summary available'))
        author = post.get('author', 'Unknown')
        url = post.get('url', '')
        visual_text = post.get('visual_text', '')
        audio_text = post.get('audio_text', '')
        page_count = post.get('page_count', 0)
        has_video = post.get('has_video', False)
        
        badge = self._get_importance_badge(importance) if include_importance else ""
        post_header = f"Post #{post_number}"

        metadata_parts = []
        if author:
            metadata_parts.append(f"<b>Author:</b> {author}")
        if page_count:
            metadata_parts.append(f"<b>Slides:</b> {page_count}")
        if has_video:
            metadata_parts.append("<b>Media:</b> Video")
        if include_importance:
            rating = "★" * importance + "☆" * (5 - importance)
            metadata_parts.append(f"<b>Rating:</b> {rating} ({importance}/5)")
        if include_links and url:
            metadata_parts.append(f"<b>Source:</b> <a href='{url}' color='blue'>{url[:70]}...</a>")

        card_color = colors.HexColor('#fff8ef') if importance >= 4 else colors.HexColor('#fbfbfb')
        accent_color = colors.HexColor('#7c1d12') if importance >= 4 else colors.HexColor('#8f5d1f' if importance == 3 else '#234a72')
        summary_text = summary[:420] + ("..." if len(summary) > 420 else "")
        detail_lines = []
        if visual_text:
            detail_lines.append(f"<b>Visual context:</b> {visual_text[:180]}...")
        if audio_text:
            detail_lines.append(f"<b>Audio context:</b> {audio_text[:180]}...")

        card_rows = [
            [Paragraph(f"<b>{post_header}</b> <font color='#7c1d12'>{badge}</font>" if badge else f"<b>{post_header}</b>", self.styles['PostTitle'])],
            [Paragraph(summary_text, self.styles['CustomBody'])],
        ]
        if detail_lines:
            card_rows.append([Paragraph("<br/>".join(detail_lines), self.styles['Metadata'])])
        if metadata_parts:
            card_rows.append([Paragraph(" | ".join(metadata_parts), self.styles['Metadata'])])

        card = Table(card_rows, colWidths=[self.content_width])
        card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), card_color),
            ('BOX', (0, 0), (-1, -1), 1.1, accent_color),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(card)
        return elements
    
    def _build_footer(self) -> List:
        """Build PDF footer section."""
        elements = []
        
        elements.append(Spacer(1, 0.18 * inch))
        elements.append(Paragraph(
            "Generated by TOM (The Omniscient Monitor) | Instagram AI News Agent",
            self.styles['Metadata']
        ))
        
        return elements

    def _draw_page_decor(self, canvas, doc):
        width, height = self.page_size
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#f7f2ea'))
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        canvas.setStrokeColor(colors.HexColor('#c9b18a'))
        canvas.setLineWidth(1)
        canvas.line(self.margin_size, height - 0.42 * inch, width - self.margin_size, height - 0.42 * inch)
        canvas.line(self.margin_size, 0.55 * inch, width - self.margin_size, 0.55 * inch)
        canvas.setFillColor(colors.HexColor('#6f6f78'))
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(width - self.margin_size, 0.35 * inch, f"Page {doc.page}")
        canvas.restoreState()
    
    def generate(self, posts: List[Dict], output_dir: str, title: str = "AI News Report",
                 include_importance: bool = True, include_links: bool = True) -> str:
        """
        Generate PDF report from posts.
        
        Args:
            posts: List of post dictionaries with 'text', 'summary', 'importance', etc.
            output_dir: Directory where PDF will be saved
            title: Report title
            include_importance: Include importance ratings in report
            include_links: Include post links in report
            
        Returns:
            Path to generated PDF file
        """
        logger.info(f"Generating PDF report with {len(posts)} posts")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now()
        filename = f"instagram_ai_news_{timestamp.strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_file = output_path / filename
        
        logger.info(f"Output file: {pdf_file}")
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(pdf_file),
            pagesize=self.page_size,
            rightMargin=self.margin_size,
            leftMargin=self.margin_size,
            topMargin=self.margin_size,
            bottomMargin=self.margin_size,
            title=title,
            author="TOM (The Omniscient Monitor)",
        )
        
        # Build document elements
        elements = []
        elements.extend(self._build_header(title, timestamp))
        if posts:
            elements.extend(self._build_summary_section(posts))
            if len(posts) > 0:
                elements.append(PageBreak())
            elements.extend(self._build_posts_section(posts, include_importance, include_links))
        elements.extend(self._build_footer())
        
        # Generate PDF
        try:
            doc.build(elements, onFirstPage=self._draw_page_decor, onLaterPages=self._draw_page_decor)
            logger.info(f"PDF generated successfully: {pdf_file}")
            return str(pdf_file)
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
