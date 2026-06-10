from __future__ import annotations

import os
import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    pytesseract = importlib.import_module("pytesseract")
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None


@dataclass(slots=True)
class ScreenTextBlock:
    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int


class ScreenTools:
    """Basic screen capture and OCR utilities.

    This is a lightweight screen-reading layer: it captures the current desktop
    and extracts text so TOM can reason over visible content when the user asks
    it to read or analyze the screen.
    """

    def __init__(self):
        self.tesseract_cmd = os.environ.get("TESSERACT_CMD", "").strip()
        if self.tesseract_cmd and pytesseract:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _dependency_status(self) -> Optional[str]:
        if pyautogui is None:
            return "pyautogui is not installed"
        if pytesseract is None:
            return "pytesseract is not installed"
        if Image is None:
            return "Pillow is not installed"
        return None

    def capture_screen(self):
        if pyautogui is None:
            raise RuntimeError("pyautogui is not installed")
        screenshot = pyautogui.screenshot()
        return screenshot

    def extract_text(self) -> Dict[str, Any]:
        dependency_error = self._dependency_status()
        if dependency_error:
            return {
                "status": "error",
                "message": dependency_error,
                "text": "",
                "blocks": [],
            }

        try:
            screenshot = self.capture_screen()
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

            blocks: List[ScreenTextBlock] = []
            lines: List[str] = []
            n = len(data.get("text", []))
            for index in range(n):
                text = str(data["text"][index]).strip()
                if not text:
                    continue

                confidence_value = data.get("conf", [0] * n)[index]
                try:
                    confidence = float(confidence_value)
                except Exception:
                    confidence = -1.0

                block = ScreenTextBlock(
                    text=text,
                    confidence=confidence,
                    left=int(data.get("left", [0] * n)[index]),
                    top=int(data.get("top", [0] * n)[index]),
                    width=int(data.get("width", [0] * n)[index]),
                    height=int(data.get("height", [0] * n)[index]),
                )
                blocks.append(block)
                lines.append(text)

            visible_text = " ".join(lines).strip()
            return {
                "status": "success",
                "message": "Screen text extracted",
                "text": visible_text,
                "blocks": [block.__dict__ for block in blocks],
                "text_length": len(visible_text),
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Failed to read screen text: {exc}",
                "text": "",
                "blocks": [],
            }

    def summarize_screen(self, max_chars: int = 1200) -> Dict[str, Any]:
        result = self.extract_text()
        if result.get("status") != "success":
            return result

        text = str(result.get("text", ""))
        summary = text[:max_chars]
        return {
            "status": "success",
            "message": "Screen summary created",
            "summary": summary,
            "text_length": result.get("text_length", 0),
            "blocks": result.get("blocks", []),
        }
