"""Gate-4 helper tests — no ffmpeg binary, no network.

Covers the pure helpers behind validate(): the size threshold, the
`ffmpeg -i` stderr parser on recorded fixtures, brightness sampling
on synthetic images, and the per-scene SRT writer the renderer owns.
"""
from pathlib import Path

from PIL import Image

from app.providers.qa_gate import (
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    MAX_DURATION_SEC,
    MIN_DURATION_SEC,
    MIN_SIZE_BYTES,
    _scene_spans,
    check_brightness_sample,
    check_size,
    check_text_overflow,
    frame_brightness,
    parse_ffmpeg_info,
    validate,
)
from app.providers.renderer_pillow import format_timestamp, write_scene_srt
from types import SimpleNamespace

VALID_STDERR = """\
ffmpeg version 6.0 Copyright (c) 2000-2023
  Duration: 00:00:32.50, start: 0.000000, bitrate: 605 kb/s
  Stream #0:0(und): Video: h264 (Main) (avc1 / 0x31637661), yuv420p, 1280x720, 500 kb/s, 24 fps
  Stream #0:1(und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 128 kb/s
"""

NO_AUDIO_STDERR = """\
ffmpeg version 6.0 Copyright (c) 2000-2023
  Duration: 00:00:31.00, start: 0.000000, bitrate: 480 kb/s
  Stream #0:0(und): Video: h264 (Main) (avc1 / 0x31637661), yuv420p, 1280x720, 480 kb/s, 24 fps
"""


def test_size_threshold(tmp_path: Path):
    assert MIN_SIZE_BYTES == 200_000  # drift breaks the build, not just weakens it
    tiny = tmp_path / "tiny.mp4"
    tiny.write_bytes(b"0" * (MIN_SIZE_BYTES - 1))
    assert check_size(tiny)["ok"] is False
    edge = tmp_path / "edge.mp4"
    edge.write_bytes(b"0" * MIN_SIZE_BYTES)
    assert check_size(edge)["ok"] is False  # strict `>` gate
    big = tmp_path / "big.mp4"
    big.write_bytes(b"0" * (MIN_SIZE_BYTES + 1))
    assert check_size(big)["ok"] is True
    assert check_size(tmp_path / "missing.mp4")["ok"] is False


def test_threshold_constants_exact():
    assert MIN_DURATION_SEC == 25.0
    assert MAX_DURATION_SEC == 60.0
    assert BRIGHTNESS_MIN == 15.0
    assert BRIGHTNESS_MAX == 240.0

def test_parse_valid_stream():
    info = parse_ffmpeg_info(VALID_STDERR)
    assert info["duration_sec"] == 32.5
    assert info["has_video"] and info["has_audio"]
    assert info["video_codec"] == "h264"
    assert info["audio_codec"] == "aac"


def test_parse_no_audio_stream():
    info = parse_ffmpeg_info(NO_AUDIO_STDERR)
    assert info["duration_sec"] == 31.0
    assert info["has_audio"] is False
    assert info["audio_codec"] is None


def test_parse_garbage_stderr():
    info = parse_ffmpeg_info("nothing to see here")
    assert info["duration_sec"] is None
    assert info["has_video"] is False


def _solid(tmp_path: Path, name: str, gray: int) -> Path:
    path = tmp_path / name
    Image.new("RGB", (64, 36), (gray, gray, gray)).save(path)
    return path


def test_brightness_mid_passes(tmp_path: Path):
    mid = _solid(tmp_path, "mid.png", 120)
    assert 15.0 <= frame_brightness(mid) <= 240.0
    assert check_brightness_sample([mid])["ok"] is True


def test_brightness_extremes_fail(tmp_path: Path):
    black = _solid(tmp_path, "black.png", 0)
    white = _solid(tmp_path, "white.png", 255)
    assert check_brightness_sample([black])["ok"] is False
    assert check_brightness_sample([white])["ok"] is False
    assert check_brightness_sample([])["ok"] is False


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(61.5) == "00:01:01,500"
    assert format_timestamp(32.5) == "00:00:32,500"


def test_scene_srt_writer(tmp_path: Path):
    narration = "Acids release hydrogen ions below pH seven in water."
    out = write_scene_srt(tmp_path / "scene_00.srt", 0, 0.0, 6.0, narration)
    text = out.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:06,000" in text
    assert "hydrogen" in text

def test_scene_spans_split_and_fallback():
    spans = _scene_spans(30.0, [5.0, 5.0, 5.0, 5.0, 5.0, 5.0])
    assert len(spans) == 6
    assert spans[0][0] == 0.0 and spans[-1][1] == 30.0
    assert spans[1][0] == spans[0][1]  # contiguous, no gaps to hide in
    assert _scene_spans(30.0, None) == [(0.0, 30.0)]


def _stub_scene(**kw):
    base = {
        "id": "s1",
        "title": "Acids Below Seven",
        "bullets": ["Lemon juice sits near pH two"],
        "narration": "Acids release hydrogen ions below pH seven in water every day.",
    }
    return SimpleNamespace(**{**base, **kw})


def test_text_overflow_passes_clean_scene():
    assert check_text_overflow([_stub_scene()]) == {"ok": True, "problems": []}


def test_text_overflow_fails_unwrappable_title():
    bad = _stub_scene(title="X" * 200)  # one word: shrink floor cannot save it
    result = check_text_overflow([bad])
    assert result["ok"] is False
    assert result["problems"] and "s1" in result["problems"][0]


def test_validate_entrypoint_exists():
    assert callable(validate)
