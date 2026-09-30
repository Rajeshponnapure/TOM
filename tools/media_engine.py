"""
TOM Media Engine -- real video and photo editing.

Video editing runs through ffmpeg (an external binary, detected the same way
tools/file_analyzer.py already finds ffprobe: bare command on PATH, then
common Windows install locations). Photo editing runs through Pillow
in-process. Every operation waits for completion, checks the process exit
code, and verifies the declared output file actually exists on disk before
reporting success -- the lesson from the Blender engine, which used to
fire-and-forget a subprocess and report success the instant it merely
launched, applied here from the start instead of after the fact.

This is NOT a GUI non-linear editor (Premiere/DaVinci/Photoshop) -- it is a
real, scriptable, chat-driven engine: trim/concat/convert/caption/color for
video, crop/resize/filter/watermark/convert for photos.
"""
import os
import subprocess
import uuid
from typing import Any, Dict, List, Optional

from tools.project_paths import project_path_str

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

_FFMPEG_CANDIDATES = ["ffmpeg", r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"]
_FFPROBE_CANDIDATES = ["ffprobe", r"C:\ffmpeg\bin\ffprobe.exe", r"C:\Program Files\ffmpeg\bin\ffprobe.exe"]


def _ok(**extra) -> Dict[str, Any]:
    out = {"status": "success"}
    out.update(extra)
    return out


def _err(message: str, **extra) -> Dict[str, Any]:
    out = {"status": "error", "message": message}
    out.update(extra)
    return out


class MediaEngine:
    """Real video (ffmpeg) and photo (Pillow) editing."""

    def __init__(self):
        self.ffmpeg_path = self._find_binary(_FFMPEG_CANDIDATES)
        self.ffprobe_path = self._find_binary(_FFPROBE_CANDIDATES)

    @staticmethod
    def _find_binary(candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            try:
                subprocess.run([cand, "-version"], capture_output=True, timeout=5,
                                creationflags=_NO_WINDOW)
                return cand
            except Exception:
                continue
        return None

    def video_available(self) -> bool:
        return self.ffmpeg_path is not None

    def photo_available(self) -> bool:
        return _HAS_PIL

    @staticmethod
    def _out_dir(slug: str) -> str:
        safe_slug = "".join(c if c.isalnum() else "_" for c in slug.lower()).strip("_")[:40] or "media"
        return project_path_str("tom_brain", "media_output", f"{safe_slug}_{uuid.uuid4().hex[:8]}")

    # ── ffmpeg execution (shared by every video operation) ─────────────────
    def _run_ffmpeg(self, args: List[str], output_path: str, timeout: int = 300) -> Dict[str, Any]:
        if not self.ffmpeg_path:
            return _err("ffmpeg is not installed (or not found on PATH). "
                        "Install it from https://ffmpeg.org/download.html and retry.")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [self.ffmpeg_path, "-y", *args, output_path]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                  creationflags=_NO_WINDOW)
        except subprocess.TimeoutExpired:
            return _err(f"ffmpeg did not finish within {timeout}s.")
        except Exception as exc:
            return _err(str(exc))
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip()[-800:]
            return _err(f"ffmpeg exited with code {proc.returncode}: {tail}")
        # ffmpeg can exit 0 while still not having written the file (e.g. an
        # unsupported filter combination that it treats as a warning) -- the
        # exact failure mode the Blender engine had. Verify on disk, not on
        # trust in the exit code alone.
        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            tail = (proc.stderr or "").strip()[-500:]
            return _err(f"ffmpeg reported success but {output_path} was not created. {tail}")
        return _ok(path=output_path, message=f"Saved to {output_path}",
                   stderr_tail=(proc.stderr or "").strip()[-300:])

    # ── Video operations ────────────────────────────────────────────────────
    def trim_video(self, input_path: str, start: float, duration: float) -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("trim")
        ext = os.path.splitext(input_path)[1] or ".mp4"
        output_path = os.path.join(out_dir, f"trimmed{ext}")
        return self._run_ffmpeg(
            ["-ss", str(start), "-i", input_path, "-t", str(duration), "-c", "copy"], output_path)

    def convert_video_format(self, input_path: str, target_format: str) -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("convert")
        output_path = os.path.join(out_dir, f"converted.{target_format.lstrip('.')}")
        return self._run_ffmpeg(["-i", input_path], output_path)

    def concat_videos(self, input_paths: List[str]) -> Dict[str, Any]:
        missing = [p for p in input_paths if not os.path.isfile(p)]
        if missing:
            return _err(f"Input file(s) not found: {', '.join(missing)}")
        if len(input_paths) < 2:
            return _err("Need at least 2 videos to concatenate.")
        out_dir = self._out_dir("concat")
        os.makedirs(out_dir, exist_ok=True)
        list_path = os.path.join(out_dir, "concat_list.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in input_paths:
                escaped = os.path.abspath(p).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")
        ext = os.path.splitext(input_paths[0])[1] or ".mp4"
        output_path = os.path.join(out_dir, f"concatenated{ext}")
        return self._run_ffmpeg(
            ["-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy"], output_path)

    def add_text_overlay(self, input_path: str, text: str, position: str = "bottom") -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("caption")
        ext = os.path.splitext(input_path)[1] or ".mp4"
        output_path = os.path.join(out_dir, f"captioned{ext}")
        y = {"top": "40", "center": "(h-text_h)/2", "bottom": "h-th-40"}.get(position, "h-th-40")
        safe_text = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        vf = (f"drawtext=text='{safe_text}':fontcolor=white:fontsize=32:"
              f"box=1:boxcolor=black@0.5:boxborderw=8:x=(w-text_w)/2:y={y}")
        return self._run_ffmpeg(["-i", input_path, "-vf", vf, "-codec:a", "copy"], output_path)

    def extract_audio(self, input_path: str) -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("audio")
        output_path = os.path.join(out_dir, "audio.mp3")
        return self._run_ffmpeg(["-i", input_path, "-vn", "-acodec", "libmp3lame"], output_path)

    def resize_video(self, input_path: str, width: int, height: int) -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("resize")
        ext = os.path.splitext(input_path)[1] or ".mp4"
        output_path = os.path.join(out_dir, f"resized{ext}")
        return self._run_ffmpeg(["-i", input_path, "-vf", f"scale={width}:{height}"], output_path)

    def adjust_video(self, input_path: str, brightness: float = 0.0,
                      contrast: float = 1.0, saturation: float = 1.0) -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("adjust")
        ext = os.path.splitext(input_path)[1] or ".mp4"
        output_path = os.path.join(out_dir, f"adjusted{ext}")
        vf = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}"
        return self._run_ffmpeg(["-i", input_path, "-vf", vf, "-codec:a", "copy"], output_path)

    def set_video_volume(self, input_path: str, factor: float) -> Dict[str, Any]:
        if not os.path.isfile(input_path):
            return _err(f"Input file not found: {input_path}")
        out_dir = self._out_dir("volume")
        ext = os.path.splitext(input_path)[1] or ".mp4"
        output_path = os.path.join(out_dir, f"volume{ext}")
        return self._run_ffmpeg(["-i", input_path, "-af", f"volume={factor}"], output_path)

    # ── Photo operations (Pillow, in-process) ───────────────────────────────
    def _open_image(self, input_path: str):
        if not _HAS_PIL:
            return None, _err("Pillow is not installed.")
        if not os.path.isfile(input_path):
            return None, _err(f"Input file not found: {input_path}")
        try:
            return Image.open(input_path), None
        except Exception as exc:
            return None, _err(f"Could not open image: {exc}")

    def _save_image(self, img, out_dir: str, filename: str) -> Dict[str, Any]:
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, filename)
        try:
            if img.mode in ("RGBA", "P") and filename.lower().endswith((".jpg", ".jpeg")):
                img = img.convert("RGB")
            img.save(output_path)
        except Exception as exc:
            return _err(f"Could not save image: {exc}")
        if not os.path.isfile(output_path):
            return _err(f"Save reported no error but {output_path} was not created.")
        return _ok(path=output_path, message=f"Saved to {output_path}")

    def resize_image(self, input_path: str, width: int, height: int) -> Dict[str, Any]:
        img, err = self._open_image(input_path)
        if err:
            return err
        resized = img.resize((width, height))
        ext = os.path.splitext(input_path)[1] or ".png"
        return self._save_image(resized, self._out_dir("resize"), f"resized{ext}")

    def crop_image(self, input_path: str, left: int, top: int, right: int, bottom: int) -> Dict[str, Any]:
        img, err = self._open_image(input_path)
        if err:
            return err
        if right <= left or bottom <= top:
            return _err("Crop box must have right>left and bottom>top.")
        cropped = img.crop((left, top, right, bottom))
        ext = os.path.splitext(input_path)[1] or ".png"
        return self._save_image(cropped, self._out_dir("crop"), f"cropped{ext}")

    _FILTERS = {
        "grayscale": lambda img: img.convert("L").convert(img.mode if img.mode != "L" else "RGB"),
        "blur": lambda img: img.filter(ImageFilter.GaussianBlur(4)) if _HAS_PIL else img,
        "sharpen": lambda img: img.filter(ImageFilter.SHARPEN) if _HAS_PIL else img,
        "smooth": lambda img: img.filter(ImageFilter.SMOOTH) if _HAS_PIL else img,
        "contour": lambda img: img.filter(ImageFilter.CONTOUR) if _HAS_PIL else img,
        "brighten": lambda img: ImageEnhance.Brightness(img).enhance(1.4) if _HAS_PIL else img,
        "darken": lambda img: ImageEnhance.Brightness(img).enhance(0.7) if _HAS_PIL else img,
        "high_contrast": lambda img: ImageEnhance.Contrast(img).enhance(1.6) if _HAS_PIL else img,
        "saturate": lambda img: ImageEnhance.Color(img).enhance(1.6) if _HAS_PIL else img,
        "sepia": None,  # handled specially below
    }

    def apply_filter(self, input_path: str, filter_name: str) -> Dict[str, Any]:
        img, err = self._open_image(input_path)
        if err:
            return err
        name = filter_name.lower().strip()
        if name == "sepia":
            gray = img.convert("L")
            filtered = Image.merge("RGB", (
                gray.point(lambda p: min(255, int(p * 1.07))),
                gray.point(lambda p: min(255, int(p * 0.90))),
                gray.point(lambda p: min(255, int(p * 0.65))),
            ))
        elif name in self._FILTERS:
            filtered = self._FILTERS[name](img)
        else:
            return _err(f"Unknown filter '{filter_name}'. Choices: {', '.join(sorted(self._FILTERS))}, sepia")
        ext = os.path.splitext(input_path)[1] or ".png"
        return self._save_image(filtered, self._out_dir(f"filter_{name}"), f"{name}{ext}")

    def add_watermark(self, input_path: str, text: str, position: str = "bottom-right") -> Dict[str, Any]:
        img, err = self._open_image(input_path)
        if err:
            return err
        base = img.convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("arial.ttf", max(18, base.size[0] // 30))
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = 12
        positions = {
            "bottom-right": (base.size[0] - tw - margin, base.size[1] - th - margin),
            "bottom-left": (margin, base.size[1] - th - margin),
            "top-right": (base.size[0] - tw - margin, margin),
            "top-left": (margin, margin),
            "center": ((base.size[0] - tw) // 2, (base.size[1] - th) // 2),
        }
        xy = positions.get(position, positions["bottom-right"])
        draw.text(xy, text, font=font, fill=(255, 255, 255, 180))
        watermarked = Image.alpha_composite(base, overlay)
        ext = os.path.splitext(input_path)[1] or ".png"
        if watermarked.mode == "RGBA" and ext.lower() in (".jpg", ".jpeg"):
            watermarked = watermarked.convert("RGB")
        return self._save_image(watermarked, self._out_dir("watermark"), f"watermarked{ext}")

    def convert_image_format(self, input_path: str, target_format: str) -> Dict[str, Any]:
        img, err = self._open_image(input_path)
        if err:
            return err
        ext = "." + target_format.lstrip(".").lower()
        return self._save_image(img, self._out_dir("convert"), f"converted{ext}")

    def rotate_image(self, input_path: str, degrees: float) -> Dict[str, Any]:
        img, err = self._open_image(input_path)
        if err:
            return err
        rotated = img.rotate(-degrees, expand=True)
        ext = os.path.splitext(input_path)[1] or ".png"
        return self._save_image(rotated, self._out_dir("rotate"), f"rotated{ext}")
