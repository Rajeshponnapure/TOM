"""tools/media_engine.py -- real video (ffmpeg) and photo (Pillow) editing.

Before this, TOM had zero real video/photo editing: skills/39-media-production-
skills.md is pure reference text about Premiere Pro/DaVinci Resolve/Photoshop,
misclassified by SkillManager as tool_backed against blender_control + os_tools
(neither of which can touch a video or photo file) purely because the word
"windows" appears in "power windows" (a DaVinci color-grading term) and "3d"
appears in a section heading -- both keyword-matching false positives unrelated
to the skill's actual subject.

Photo operations run through Pillow (installed) and are tested for real, with
pixel-level assertions -- not just "a file exists". Video operations need
ffmpeg, which is not installed on this dev machine, so those are tested against
a faked subprocess that mirrors the real contract (ffmpeg invoked as
`ffmpeg -y <args> <output_path>`), applying the same lesson the Blender fix
already established: waiting for completion, checking the exit code, and
verifying the declared output file actually exists on disk before reporting
success -- built in from the start here, not bolted on after a bug.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

# Pillow is optional and not in requirements-ci.txt; skip the whole module
# (rather than erroring at collection) when it's absent, matching how
# test_data_analysis.py / test_document_creator.py handle matplotlib / pptx.
pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

import tools.media_engine as mediamod  # noqa: E402
from tools.media_engine import MediaEngine  # noqa: E402


@pytest.fixture
def eng(monkeypatch, tmp_path):
    monkeypatch.setattr(mediamod, "project_path_str",
                         lambda *parts: str(tmp_path.joinpath(*parts)))
    return MediaEngine()


@pytest.fixture
def sample_photo(tmp_path):
    path = tmp_path / "sample.png"
    Image.new("RGB", (300, 200), (60, 120, 200)).save(path)
    return str(path)


# ── Photo editing: real Pillow execution, pixel-level checks ───────────────

def test_photo_available_when_pillow_installed(eng):
    assert eng.photo_available() is True


def test_resize_image_produces_exact_dimensions(eng, sample_photo):
    res = eng.resize_image(sample_photo, 100, 80)
    assert res["status"] == "success"
    assert os.path.isfile(res["path"])
    assert Image.open(res["path"]).size == (100, 80)


def test_crop_image_produces_exact_dimensions(eng, sample_photo):
    res = eng.crop_image(sample_photo, 10, 10, 110, 90)
    assert res["status"] == "success"
    assert Image.open(res["path"]).size == (100, 80)


def test_crop_rejects_an_inverted_box(eng, sample_photo):
    res = eng.crop_image(sample_photo, 100, 100, 50, 50)
    assert res["status"] == "error"


def test_grayscale_filter_actually_desaturates_pixels(eng, sample_photo):
    res = eng.apply_filter(sample_photo, "grayscale")
    assert res["status"] == "success"
    r, g, b = Image.open(res["path"]).convert("RGB").getpixel((50, 50))
    assert r == g == b


def test_unknown_filter_is_a_clear_error(eng, sample_photo):
    res = eng.apply_filter(sample_photo, "not_a_real_filter")
    assert res["status"] == "error"
    assert "Unknown filter" in res["message"]


def test_watermark_actually_changes_pixels_near_its_position(eng, sample_photo):
    res = eng.add_watermark(sample_photo, "TOM", "bottom-right")
    assert res["status"] == "success"
    img = Image.open(res["path"]).convert("RGB")
    original = (60, 120, 200)
    region = [img.getpixel((x, y)) for x in range(220, 290, 10) for y in range(160, 190, 10)]
    assert any(p != original for p in region)


def test_convert_image_format_changes_extension_and_opens(eng, sample_photo):
    res = eng.convert_image_format(sample_photo, "jpg")
    assert res["status"] == "success"
    assert res["path"].endswith(".jpg")
    Image.open(res["path"]).load()  # raises if not a valid image


def test_rotate_image_changes_dimensions_for_non_square_source(eng, sample_photo):
    res = eng.rotate_image(sample_photo, 90)
    assert res["status"] == "success"
    # a 300x200 source rotated 90 degrees (expand=True) becomes ~200x300
    w, h = Image.open(res["path"]).size
    assert w < h


def test_missing_input_file_is_reported_as_error(eng, tmp_path):
    res = eng.resize_image(str(tmp_path / "does_not_exist.png"), 10, 10)
    assert res["status"] == "error"
    assert "not found" in res["message"]


def test_two_operations_never_collide_on_output_path(eng, sample_photo):
    res1 = eng.resize_image(sample_photo, 50, 50)
    res2 = eng.resize_image(sample_photo, 50, 50)
    assert res1["path"] != res2["path"]
    assert os.path.isfile(res1["path"]) and os.path.isfile(res2["path"])


# ── Video editing: faked ffmpeg subprocess ──────────────────────────────────

def _fake_ffmpeg_that_saves(cmd, capture_output, text, timeout, creationflags):
    out_path = cmd[-1]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(b"FAKE_VIDEO")
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="frame=1")


@pytest.fixture
def sample_video(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"not a real video, just needs to exist")
    return str(path)


def test_video_unavailable_without_ffmpeg(eng):
    eng.ffmpeg_path = None
    assert eng.video_available() is False


def test_trim_video_success_reports_a_real_verifiable_path(eng, sample_video, monkeypatch):
    eng.ffmpeg_path = "FAKE_FFMPEG"
    monkeypatch.setattr(mediamod.subprocess, "run", _fake_ffmpeg_that_saves)
    res = eng.trim_video(sample_video, 0, 5)
    assert res["status"] == "success"
    assert os.path.isfile(res["path"])


def test_concat_requires_at_least_two_videos(eng, sample_video):
    eng.ffmpeg_path = "FAKE_FFMPEG"
    res = eng.concat_videos([sample_video])
    assert res["status"] == "error"


def test_exit_zero_but_no_file_is_reported_as_error_not_success(eng, sample_video, monkeypatch):
    """The exact bug class the Blender engine had, guarded against here."""
    def fake_run_silent_noop(cmd, capture_output, text, timeout, creationflags):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    eng.ffmpeg_path = "FAKE_FFMPEG"
    monkeypatch.setattr(mediamod.subprocess, "run", fake_run_silent_noop)
    res = eng.trim_video(sample_video, 0, 5)
    assert res["status"] == "error"
    assert "was not created" in res["message"]


def test_nonzero_exit_is_reported_as_error_with_diagnostic(eng, sample_video, monkeypatch):
    def fake_run_crash(cmd, capture_output, text, timeout, creationflags):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Unknown encoder 'x'")
    eng.ffmpeg_path = "FAKE_FFMPEG"
    monkeypatch.setattr(mediamod.subprocess, "run", fake_run_crash)
    res = eng.trim_video(sample_video, 0, 5)
    assert res["status"] == "error"
    assert "Unknown encoder" in res["message"]


def test_timeout_is_reported_as_error(eng, sample_video, monkeypatch):
    def fake_run_timeout(cmd, capture_output, text, timeout, creationflags):
        raise subprocess.TimeoutExpired(cmd, timeout)
    eng.ffmpeg_path = "FAKE_FFMPEG"
    monkeypatch.setattr(mediamod.subprocess, "run", fake_run_timeout)
    res = eng.trim_video(sample_video, 0, 5)
    assert res["status"] == "error"


def test_ffmpeg_not_installed_is_a_clear_error_not_a_crash(eng, sample_video):
    eng.ffmpeg_path = None
    res = eng.trim_video(sample_video, 0, 5)
    assert res["status"] == "error"
    assert "not installed" in res["message"]
