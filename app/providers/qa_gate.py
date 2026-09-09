"""QA Gate 4 — artifact integrity before a job may complete.

Thresholds live here (docs/06 §6.4): size, duration, audio presence,
frame brightness, codec strings. Duration/codec/audio come from
`ffmpeg -i` stderr parsing (never a separate metadata binary);
brightness from Pillow ImageStat over frames pulled at 25/50/75% of
the runtime. validate() returns {passed, checks}; the small helpers
are importable so unit tests cover them without any binary.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

MIN_SIZE_BYTES = 200_000
MIN_DURATION_SEC = 25.0
MAX_DURATION_SEC = 60.0
MIN_AUDIO_SEC = 20.0
BRIGHTNESS_MIN = 15.0
BRIGHTNESS_MAX = 240.0


def check_size(path: str | Path) -> dict:
    size = os.path.getsize(path) if Path(path).exists() else 0
    return {"ok": size > MIN_SIZE_BYTES, "size_bytes": size}


def parse_ffmpeg_info(stderr: str) -> dict:
    """Parse `ffmpeg -i` stderr into duration/codec/audio facts."""
    duration: float | None = None
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", stderr)
    if match:
        hours, minutes, seconds = int(match.group(1)), int(match.group(2)), float(match.group(3))
        duration = hours * 3600 + minutes * 60 + seconds
    video = re.search(r"Stream.*Video:\s*([A-Za-z0-9]+)", stderr)
    audio = re.search(r"Stream.*Audio:\s*([A-Za-z0-9]+)", stderr)
    return {
        "duration_sec": duration,
        "has_video": video is not None,
        "has_audio": audio is not None,
        "video_codec": video.group(1).lower() if video else None,
        "audio_codec": audio.group(1).lower() if audio else None,
    }


def parse_audio_time(stderr: str) -> float | None:
    """Parse AUDIO length off an audio-only null-mux run's stderr.

    Same regex style as parse_ffmpeg_info, but over the trailing `time=`
    progress of `ffmpeg -i <video> -map 0:a -f null -`, which tracks the
    audio stream alone — unlike the container `Duration:` line, which hides
    a short (or padded) audio track inside a long video.
    """
    hits = re.findall(r"time=(\d+):(\d+):([\d.]+)", stderr)
    if not hits:
        return None
    return max(int(h) * 3600 + int(m) * 60 + float(s) for h, m, s in hits)


def mp3_duration(path: str | Path) -> float | None:
    """Source-mp3 length via mutagen; None when unavailable or unreadable."""
    try:
        from mutagen.mp3 import MP3

        return float(MP3(str(path)).info.length)
    except Exception:
        return None


def _measure_audio_seconds(exe: str, video_path: str | Path) -> float | None:
    """Decode the muxed audio stream to null and report its real length."""
    try:
        proc = subprocess.run(
            [exe, "-i", str(video_path), "-map", "0:a", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return parse_audio_time(proc.stderr)

def frame_brightness(path: str | Path) -> float:
    from PIL import Image, ImageStat  # lazy: keeps QA importable without Pillow

    return ImageStat.Stat(Image.open(path).convert("L")).mean[0]


def _scene_spans(duration: float, scene_durations: list[float] | None) -> list[tuple[float, float]]:
    """Split the runtime into per-scene (start, end) spans.

    Explicit durations win (rescaled when they drift from the measured
    runtime); without them the whole video is one span, preserving the
    old 25/50/75%-of-runtime sampling for old callers.
    """
    if not scene_durations:
        return [(0.0, duration)]
    total = sum(scene_durations)
    if total <= 0:
        return [(0.0, duration)]
    scale = duration / total
    spans, start = [], 0.0
    for secs in scene_durations:
        end = start + secs * scale
        spans.append((start, end))
        start = end
    return spans


def check_text_overflow(scenes) -> dict:
    """Gate-4 text rule: no final title/bullet/subtitle box >= 90% width.

    Boxes are recomputed with the renderer's own font metrics (lazy
    import, no new dependency) at the sizes the renderer finally burns
    in, so this mirrors draw time instead of second-guessing it. Scenes
    are duck-typed (title/bullets/narration attrs) for easy unit tests.
    """
    from app.providers.renderer_pillow import (  # lazy: Pillow already optional here
        BULLET_SIZE,
        MAX_W,
        SUBTITLE_FLOOR,
        TITLE_SIZE,
        fit_font_size,
        measure_width,
        subtitle_layout,
    )

    problems = []
    for scene in scenes or []:
        size = fit_font_size(scene.title, MAX_W, TITLE_SIZE)
        if measure_width(scene.title, size) >= MAX_W:
            problems.append(f"{scene.id}: title overflows at {size}px")
        for bullet in scene.bullets[:3]:
            size = fit_font_size(bullet, MAX_W, BULLET_SIZE)
            if measure_width(bullet, size) >= MAX_W:
                problems.append(f"{scene.id}: bullet overflows at {size}px")
        size, lines = subtitle_layout(scene.narration)
        if size <= SUBTITLE_FLOOR and any(measure_width(line, size) >= MAX_W for line in lines):
            problems.append(f"{scene.id}: subtitle overflows at floor {size}px")
    return {"ok": not problems, "problems": problems}

def check_brightness_sample(paths: list[str | Path]) -> dict:
    if not paths:
        return {"ok": False, "detail": "no frames sampled"}
    values = [frame_brightness(p) for p in paths]
    bad = [v for v in values if not BRIGHTNESS_MIN <= v <= BRIGHTNESS_MAX]
    return {
        "ok": not bad,
        "mean_values": [round(v, 1) for v in values],
        "detail": "" if not bad else f"{len(bad)}/{len(values)} frames outside 15-240",
    }


def validate(video_path: Path, scene_durations: list[float] | None = None,
             script=None, audio_path: str | Path | None = None) -> dict:
    """Validate an artifact. Optional params only add checks.

    scene_durations (or script.scenes when given) enables per-scene
    brightness sampling; script enables the text-overflow check;
    audio_path (e.g. the composer's audio_full.mp3) enables the mutagen
    source-mp3 cross-check. validate(path) alone behaves as before,
    except the audio check now measures the muxed audio stream instead
    of trusting the container duration.
    """
    checks: dict[str, dict] = {}
    size = check_size(video_path)
    checks["size"] = size

    from imageio_ffmpeg import get_ffmpeg_exe  # lazy: binary path only

    exe = get_ffmpeg_exe()
    proc = subprocess.run(
        [exe, "-i", str(video_path)],
        capture_output=True, text=True, timeout=30,
    )
    info = parse_ffmpeg_info(proc.stderr)
    duration = info["duration_sec"]
    checks["duration"] = {
        "ok": duration is not None and MIN_DURATION_SEC <= duration <= MAX_DURATION_SEC,
        "duration_sec": duration,
    }
    # MIN_AUDIO_SEC (20s) derives from the Gate-4 video minimum (25s,
    # docs/06 §6.4): edge-tts concat pads plus encoder-trimmed trailing
    # silence can shave ~5s off the audible track, so audio covering
    # >=20s of a >=25s video still proves the narration is real. The
    # presence of the audio stream stays the hard gate either way.
    audio_sec = _measure_audio_seconds(exe, video_path)
    mp3_sec = mp3_duration(audio_path) if audio_path is not None else None
    checks["audio"] = {
        "ok": info["has_audio"]
        and audio_sec is not None and audio_sec >= MIN_AUDIO_SEC
        and (mp3_sec is None or mp3_sec >= MIN_AUDIO_SEC),
        "has_audio": info["has_audio"],
        "audio_codec": info["audio_codec"],
        "audio_sec": audio_sec,
        "mp3_sec": mp3_sec,
    }
    checks["codec"] = {
        "ok": info["video_codec"] == "h264" and info["audio_codec"] == "aac",
        "video_codec": info["video_codec"],
        "audio_codec": info["audio_codec"],
    }
    scenes = list(script.scenes) if script is not None else None
    spans_for = scene_durations
    if spans_for is None and scenes is not None:
        spans_for = [s.duration_sec for s in scenes]
    checks["brightness"] = _sample_brightness(video_path, duration, spans_for)
    if script is not None:
        checks["text"] = check_text_overflow(scenes)
    passed = all(check.get("ok", False) for check in checks.values())
    return {"passed": passed, "checks": checks}

def _sample_brightness(video: Path, duration: float | None,
                       scene_durations: list[float] | None = None) -> dict:
    """Sample 3 evenly-spaced frames PER SCENE so a single-scene
    blackout (e.g. scene 1 or 5) cannot hide between global samples."""
    if not duration:
        return {"ok": False, "detail": "unknown duration, cannot sample"}
    from imageio_ffmpeg import get_ffmpeg_exe

    exe = get_ffmpeg_exe()
    spans = _scene_spans(duration, scene_durations)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for s, (start, end) in enumerate(spans):
                for i, frac in enumerate((0.25, 0.5, 0.75)):
                    frame = Path(tmp) / f"qa_s{s}_{i}.png"
                    proc = subprocess.run(
                        [exe, "-y", "-ss", f"{start + (end - start) * frac:.2f}",
                         "-i", str(video), "-frames:v", "1", str(frame)],
                        capture_output=True, timeout=60,
                    )
                    if proc.returncode == 0 and frame.exists():
                        paths.append(frame)
            if not paths:
                return {"ok": False, "detail": "frame extraction failed"}
            with tempfile.TemporaryDirectory() as keep:
                copies = []
                for i, src in enumerate(paths):
                    dst = Path(keep) / f"qa_{i}.png"
                    dst.write_bytes(src.read_bytes())
                    copies.append(dst)
                result = check_brightness_sample(copies)
                result["frames_per_scene"] = 3
                result["scenes_sampled"] = len(spans)
                return result
    except subprocess.SubprocessError as exc:
        return {"ok": False, "detail": f"sampling failed: {exc}"}
