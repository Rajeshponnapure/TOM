"""
TOM Universal File Analyzer.
Reads and analyzes: images, videos, PDFs, Excel, PowerPoint, Word, audio, code, CSV, JSON, etc.
"""
import io
import os
import subprocess
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PIL import Image as PilImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import pytesseract
    _HAS_TESSERACT = True
except ImportError:
    _HAS_TESSERACT = False

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False

try:
    from pptx import Presentation
    _HAS_PPTX = True
except ImportError:
    _HAS_PPTX = False

try:
    from docx import Document
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

try:
    import openpyxl
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False


class FileAnalyzer:
    """
    Universal file analyzer supporting 15+ file types.
    Extracts text, metadata, structure, and generates summaries.
    """

    SUPPORTED_EXTENSIONS = {
        ".txt", ".csv", ".json", ".xml", ".yaml", ".yml",
        ".pdf",
        ".xlsx", ".xls",
        ".pptx", ".ppt",
        ".docx", ".doc",
        ".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h",
        ".rs", ".go", ".rb", ".php", ".swift", ".kt", ".scala", ".sh", ".bat", ".ps1",
        ".md", ".rst",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg",
        ".mp4", ".avi", ".mov", ".mkv", ".webm",
        ".mp3", ".wav", ".ogg", ".flac",
        ".sql", ".log", ".ini", ".cfg", ".toml",
    }

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg"}
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac"}
    CODE_EXTENSIONS = {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h",
                       ".rs", ".go", ".rb", ".php", ".swift", ".kt", ".scala", ".sh", ".bat", ".ps1"}

    def __init__(self):
        self._last_result: Dict[str, Any] = {}

    def analyze(self, filepath: str) -> Dict[str, Any]:
        """Analyze any supported file and return structured results."""
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "message": f"File not found: {filepath}"}

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return {"status": "error", "message": f"Unsupported file type: {ext}"}

        result = {
            "status": "success",
            "file": str(path),
            "filename": path.name,
            "extension": ext,
            "size_bytes": path.stat().st_size,
            "size_display": self._format_size(path.stat().st_size),
        }

        try:
            if ext in self.IMAGE_EXTENSIONS:
                img_result = self._analyze_image(path)
                result.update(img_result)
            elif ext in self.VIDEO_EXTENSIONS:
                vid_result = self._analyze_video(path)
                result.update(vid_result)
            elif ext in self.AUDIO_EXTENSIONS:
                aud_result = self._analyze_audio(path)
                result.update(aud_result)
            elif ext == ".pdf":
                pdf_result = self._analyze_pdf(path)
                result.update(pdf_result)
            elif ext in (".xlsx", ".xls"):
                xl_result = self._analyze_excel(path)
                result.update(xl_result)
            elif ext in (".pptx", ".ppt"):
                ppt_result = self._analyze_pptx(path)
                result.update(ppt_result)
            elif ext in (".docx", ".doc"):
                doc_result = self._analyze_docx(path)
                result.update(doc_result)
            elif ext in self.CODE_EXTENSIONS:
                code_result = self._analyze_code(path)
                result.update(code_result)
            else:
                text_result = self._analyze_text(path)
                result.update(text_result)
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Analysis failed: {e}"
            result["traceback"] = traceback.format_exc()

        self._last_result = result
        return result

    def _analyze_image(self, path: Path) -> Dict[str, Any]:
        """Analyze image file: dimensions, format, OCR text, description."""
        result = {"type": "image"}
        if _HAS_PIL:
            img = PilImage.open(str(path))
            result["dimensions"] = f"{img.width}x{img.height}"
            result["format"] = img.format
            result["mode"] = img.mode
            result["aspect_ratio"] = round(img.width / img.height, 2) if img.height > 0 else 0
            # Estimate DPI
            dpi = img.info.get("dpi", (72, 72))
            result["dpi"] = dpi

        if _HAS_TESSERACT:
            try:
                text = pytesseract.image_to_string(str(path))
                text = text.strip()
                if text:
                    result["ocr_text"] = text[:2000]
                    result["ocr_word_count"] = len(text.split())
            except Exception:
                result["ocr_text"] = ""

        # File stats
        result["extension_display"] = path.suffix.upper().replace(".", "")
        return result

    def _analyze_video(self, path: Path) -> Dict[str, Any]:
        """Analyze video file: duration, dimensions, codec using ffprobe."""
        result = {"type": "video"}
        ffprobe_paths = ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe",
                         r"C:\Program Files\ffmpeg\bin\ffprobe.exe"]
        ffprobe = None
        for fp in ffprobe_paths:
            try:
                subprocess.run([fp, "-version"], capture_output=True, timeout=5)
                ffprobe = fp
                break
            except Exception:
                continue

        if ffprobe:
            try:
                cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
                       "-show_format", "-show_streams", str(path)]
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                import json as j
                data = j.loads(out.stdout)
                streams = data.get("streams", [])
                fmt = data.get("format", {})
                for s in streams:
                    if s.get("codec_type") == "video":
                        result["video_codec"] = s.get("codec_name", "unknown")
                        result["width"] = s.get("width", 0)
                        result["height"] = s.get("height", 0)
                        # SECURITY: never eval() external metadata — parse "num/den" safely.
                        _rate = s.get("avg_frame_rate", "0/1")
                        if "/" in _rate:
                            try:
                                _num, _den = _rate.split("/", 1)
                                result["fps"] = round(float(_num) / float(_den), 3) if float(_den) != 0 else 0
                            except (ValueError, ZeroDivisionError):
                                result["fps"] = 0
                        else:
                            result["fps"] = 0
                    elif s.get("codec_type") == "audio":
                        result["audio_codec"] = s.get("codec_name", "unknown")
                        result["audio_channels"] = s.get("channels", 0)
                duration = float(fmt.get("duration", 0))
                result["duration_seconds"] = round(duration, 1)
                mins, secs = divmod(int(duration), 60)
                result["duration_display"] = f"{mins}m {secs}s"
                result["bitrate"] = fmt.get("bit_rate", "unknown")
            except Exception:
                result["duration_display"] = "unknown"
        else:
            result["note"] = "ffprobe not found — install FFmpeg for full video analysis"
        return result

    def _analyze_audio(self, path: Path) -> Dict[str, Any]:
        """Analyze audio file: duration, sample rate, channels."""
        result = {"type": "audio"}
        ffprobe_paths = ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe"]
        ffprobe = None
        for fp in ffprobe_paths:
            try:
                subprocess.run([fp, "-version"], capture_output=True, timeout=5)
                ffprobe = fp
                break
            except Exception:
                continue

        if ffprobe:
            try:
                cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
                       "-show_format", "-show_streams", str(path)]
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                import json as j
                data = j.loads(out.stdout)
                fmt = data.get("format", {})
                duration = float(fmt.get("duration", 0))
                result["duration_seconds"] = round(duration, 1)
                mins, secs = divmod(int(duration), 60)
                result["duration_display"] = f"{mins}m {secs}s"
                for s in data.get("streams", []):
                    if s.get("codec_type") == "audio":
                        result["codec"] = s.get("codec_name", "unknown")
                        result["sample_rate"] = s.get("sample_rate", "unknown")
                        result["channels"] = s.get("channels", 0)
            except Exception:
                pass
        result["extension_display"] = path.suffix.upper().replace(".", "")
        return result

    def _analyze_pdf(self, path: Path) -> Dict[str, Any]:
        """Analyze PDF: page count, text extraction, table extraction."""
        result = {"type": "pdf"}
        text_content = []

        if _HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(str(path)) as pdf:
                    result["page_count"] = len(pdf.pages)
                    result["is_encrypted"] = pdf.metadata.get("encrypted", False)
                    total_text = []
                    total_tables = 0
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            total_text.append(t)
                        tables = page.extract_tables()
                        total_tables += len(tables)
                    result["table_count"] = total_tables
                    text_content = total_text
            except Exception:
                try:
                    import PyPDF2
                    with open(str(path), "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        result["page_count"] = len(reader.pages)
                        for p in reader.pages:
                            text_content.append(p.extract_text() or "")
                except ImportError:
                    text_content = ["PDF analysis requires pdfplumber or PyPDF2"]
        else:
            result["note"] = "Install pdfplumber for detailed PDF analysis: pip install pdfplumber"

        full_text = "\n".join(text_content)
        result["text_length"] = len(full_text)
        result["word_count"] = len(full_text.split())
        result["preview"] = full_text[:1500]
        return result

    def _analyze_excel(self, path: Path) -> Dict[str, Any]:
        """Analyze Excel file: sheets, columns, row counts, formulas."""
        result = {"type": "spreadsheet"}
        sheets_info = []

        if _HAS_PANDAS:
            xls = pd.ExcelFile(str(path))
            result["sheet_count"] = len(xls.sheet_names)
            result["sheet_names"] = xls.sheet_names

            for sheet in xls.sheet_names[:10]:
                try:
                    df = pd.read_excel(xls, sheet_name=sheet, nrows=1000)
                    info = {
                        "name": sheet,
                        "rows": len(df),
                        "columns": len(df.columns),
                        "column_names": list(df.columns[:20]),
                    }
                    # Count total rows in sheet
                    try:
                        if _HAS_OPENPYXL:
                            wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
                            ws = wb[sheet]
                            info["total_rows_estimate"] = ws.max_row
                            info["total_cols_estimate"] = ws.max_column
                            wb.close()
                    except Exception:
                        pass
                    sheets_info.append(info)
                except Exception:
                    sheets_info.append({"name": sheet, "error": "Could not read"})

        result["sheets"] = sheets_info
        result["has_formulas"] = self._check_excel_formulas(str(path))
        return result

    def _check_excel_formulas(self, path: str) -> bool:
        """Check if Excel file contains formulas."""
        if not _HAS_OPENPYXL:
            return False
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
            for ws in wb.worksheets:
                for row in ws.iter_rows(max_row=10, max_col=10):
                    for cell in row:
                        if isinstance(cell.value, str) and cell.value.startswith("="):
                            wb.close()
                            return True
            wb.close()
        except Exception:
            pass
        return False

    def _analyze_pptx(self, path: Path) -> Dict[str, Any]:
        """Analyze PowerPoint: slide count, text extraction, image count."""
        result = {"type": "presentation"}
        if _HAS_PPTX:
            try:
                prs = Presentation(str(path))
                result["slide_count"] = len(prs.slides)
                result["slide_width"] = prs.slide_width
                result["slide_height"] = prs.slide_height
                slides_text = []
                image_count = 0
                for slide in prs.slides:
                    slide_text = []
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            slide_text.append(shape.text.strip())
                        if shape.shape_type == 13:  # picture
                            image_count += 1
                    slides_text.append("\n".join(slide_text))
                result["image_count"] = image_count
                result["text_preview"] = "\n".join(slides_text[:3])[:2000]
            except Exception as e:
                result["error"] = str(e)
        else:
            result["note"] = "Install python-pptx for PPTX analysis: pip install python-pptx"
        return result

    def _analyze_docx(self, path: Path) -> Dict[str, Any]:
        """Analyze Word document: paragraph count, text extraction, tables."""
        result = {"type": "document"}
        if _HAS_DOCX:
            try:
                doc = Document(str(path))
                result["paragraph_count"] = len(doc.paragraphs)
                result["table_count"] = len(doc.tables)
                result["section_count"] = len(doc.sections)
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                result["text_length"] = len(text)
                result["word_count"] = len(text.split())
                result["preview"] = text[:1500]
            except Exception as e:
                result["error"] = str(e)
        else:
            result["note"] = "Install python-docx for DOCX analysis: pip install python-docx"
        return result

    def _analyze_code(self, path: Path) -> Dict[str, Any]:
        """Analyze code file: language, line count, complexity."""
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".html": "HTML", ".css": "CSS", ".java": "Java",
            ".cpp": "C++", ".c": "C", ".h": "C/C++ Header",
            ".rs": "Rust", ".go": "Go", ".rb": "Ruby", ".php": "PHP",
            ".swift": "Swift", ".kt": "Kotlin", ".scala": "Scala",
            ".sh": "Shell", ".bat": "Batch", ".ps1": "PowerShell",
        }
        result = {"type": "code"}
        result["language"] = ext_map.get(path.suffix.lower(), "Unknown")
        try:
            with open(str(path), "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            lines = content.split("\n")
            result["line_count"] = len(lines)
            result["character_count"] = len(content)
            non_empty = [l for l in lines if l.strip()]
            result["code_lines"] = len(non_empty)
            comment_lines = sum(1 for l in lines if l.strip().startswith(("#", "//", "/*", "*", "--", "%", "\"")))
            result["comment_lines"] = comment_lines
            result["preview"] = "\n".join(lines[:30])

            # Simple function/class detection
            import re
            funcs = re.findall(r"^(?:def |class |function |func |pub fn |fn )\w+", content, re.MULTILINE)
            result["definitions_found"] = funcs[:20]
        except Exception as e:
            result["error"] = str(e)
        return result

    def _analyze_text(self, path: Path) -> Dict[str, Any]:
        """Analyze text file: line count, word count, encoding."""
        result = {"type": "text"}
        try:
            with open(str(path), "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            lines = content.split("\n")
            result["line_count"] = len(lines)
            result["word_count"] = len(content.split())
            result["character_count"] = len(content)
            result["preview"] = content[:2000]
            # Detect format
            if path.suffix == ".csv":
                result["format"] = "CSV"
                if _HAS_PANDAS:
                    try:
                        df = pd.read_csv(path, nrows=5)
                        result["csv_columns"] = list(df.columns)
                        result["csv_rows_estimate"] = sum(1 for _ in open(path)) - 1
                    except Exception:
                        pass
            elif path.suffix == ".json":
                result["format"] = "JSON"
                try:
                    import json as j
                    data = j.loads(content)
                    result["json_type"] = type(data).__name__
                    result["json_keys"] = list(data.keys())[:20] if isinstance(data, dict) else len(data)
                except Exception:
                    pass
        except Exception as e:
            result["error"] = str(e)
        return result

    def extract_text(self, filepath: str) -> str:
        """Extract plain text from any supported file for LLM processing."""
        result = self.analyze(filepath)
        if result.get("status") != "success":
            return f"Error: {result.get('message', 'Unknown error')}"

        text_parts = [f"=== {result.get('filename', 'File')} ===\n"]

        # Image - use OCR
        if result.get("type") == "image":
            ocr = result.get("ocr_text", "")
            text_parts.append(ocr)

        # PDF
        elif result.get("type") == "pdf":
            text_parts.append(result.get("preview", ""))

        # Document
        elif result.get("type") == "document":
            text_parts.append(result.get("preview", ""))

        # Code
        elif result.get("type") == "code":
            text_parts.append(result.get("preview", ""))

        # Text
        elif result.get("type") == "text":
            text_parts.append(result.get("preview", ""))

        # Spreadsheet
        elif result.get("type") == "spreadsheet":
            for s in result.get("sheets", []):
                text_parts.append(f"\nSheet: {s.get('name')}")
                text_parts.append(f"Columns: {', '.join(str(c) for c in s.get('column_names', []))}")

        # Presentation
        elif result.get("type") == "presentation":
            text_parts.append(result.get("text_preview", ""))

        # Audio - note about content
        elif result.get("type") == "audio":
            text_parts.append(f"Audio file: {result.get('duration_display', 'unknown duration')}")

        return "\n".join(text_parts)

    def summarize(self, filepath: str) -> str:
        """Generate a concise summary of the file."""
        result = self.analyze(filepath)
        if result.get("status") != "success":
            return f"Cannot analyze: {result.get('message', 'Unknown error')}"

        parts = [f"📄 {result['filename']} ({result['size_display']})"]

        if result.get("type") == "image":
            parts.append(f"📷 Image - {result.get('dimensions', '?')} {result.get('format', '')}")
            if result.get("ocr_word_count", 0) > 0:
                parts.append(f"📝 OCR: {result['ocr_word_count']} words detected")

        elif result.get("type") == "pdf":
            parts.append(f"📕 PDF - {result.get('page_count', '?')} pages, "
                         f"{result.get('word_count', '?')} words")
            if result.get("table_count", 0) > 0:
                parts.append(f"📊 {result['table_count']} tables found")

        elif result.get("type") == "spreadsheet":
            sheets = result.get("sheets", [])
            parts.append(f"📊 Spreadsheet - {result.get('sheet_count', '?')} sheets")
            for s in sheets[:3]:
                parts.append(f"  ├ {s.get('name')}: {s.get('columns', '?')} cols")
            if result.get("has_formulas"):
                parts.append("  └ Contains formulas")

        elif result.get("type") == "presentation":
            parts.append(f"📽️ Presentation - {result.get('slide_count', '?')} slides")
            if result.get("image_count", 0) > 0:
                parts.append(f"  └ {result['image_count']} images")

        elif result.get("type") == "document":
            parts.append(f"📝 Document - {result.get('paragraph_count', '?')} paragraphs, "
                         f"{result.get('word_count', '?')} words")

        elif result.get("type") == "code":
            parts.append(f"💻 {result.get('language', 'Code')} - "
                         f"{result.get('line_count', '?')} lines, "
                         f"{result.get('code_lines', '?')} code lines")
            defs = result.get("definitions_found", [])
            if defs:
                parts.append(f"  └ Defines: {', '.join(defs[:5])}")

 