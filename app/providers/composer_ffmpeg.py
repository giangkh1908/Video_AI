"""FFmpeg composer — segments, concat, audio mux, fades, thumbnail.

Everything runs through the imageio-ffmpeg binary; no system install
and no metadata reader beyond `ffmpeg -i` stderr (parsed by qa_gate).
Per scene: frames become a 24fps H.264 segment, per-scene mp3s join
with a 0.3s silence pad into audio_full.mp3, then one mux applies a
0.4s fade in/out, AAC audio and faststart for streaming. The thumbnail
comes from the middle frame. Duration is read back off the finished
mp4 so QA sees the same number the file actually carries.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.providers.qa_gate import parse_ffmpeg_info

FPS = 24
PAD_SEC = 0.3
FADE_SEC = 0.4

def _q(p: Path | str) -> str:
    """Quote a path for an ffmpeg concat list file."""
    return Path(p).resolve().as_posix().replace("'", "'\\''")


def _discard(path: str | Path) -> None:
    """Best-effort temp-file removal; cleanup must never fail a compose."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def _exe() -> str:
    from imageio_ffmpeg import get_ffmpeg_exe  # lazy: binary path only

    return get_ffmpeg_exe()


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
    except subprocess.CalledProcessError as exc:
        tail = (exc.stderr or "")[-1500:]
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)[:300]} ... {tail}") from exc
    except subprocess.SubprocessError as exc:
        raise RuntimeError(f"ffmpeg failed: {exc}") from exc


class Composer:
    def compose(
        self,
        frames_by_scene: list[list[Path]],
        audio_paths: list[Path],
        out_dir: Path,
    ) -> dict:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        exe = _exe()
        segments = [
            self._segment(exe, frames, out / f"seg_{i:02d}.mp4")
            for i, frames in enumerate(frames_by_scene)
            if frames
        ]
        if not segments:
            raise RuntimeError("no frames to compose")
        video_cut = self._concat(exe, segments, out / "video_cut.mp4", stream="v")
        audio_full = self._audio_track(exe, [Path(p) for p in audio_paths], out, len(segments))
        # Fade-out is timed off the probed cut: the xfade chain shortens the
        # timeline by (n-1)*FADE_SEC, so a pre-xfade frame-count estimate pins
        # fade=t=out past the end and it never triggers.
        try:
            cut_duration = self._probe_duration(exe, video_cut)
        except RuntimeError:
            cut_duration = sum(len(f) for f in frames_by_scene) / FPS
        start_out = max(0.0, cut_duration - FADE_SEC)
        video_path = out / "video.mp4"
        _run([
            exe, "-y", "-i", str(video_cut), "-i", str(audio_full),
            "-vf", f"fade=t=in:st=0:d={FADE_SEC},fade=t=out:st={start_out:.2f}:d={FADE_SEC}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-movflags", "+faststart", "-shortest", str(video_path),
        ])
        duration = self._probe_duration(exe, video_path)
        thumb_path = out / "thumb.jpg"
        _run([exe, "-y", "-ss", f"{duration / 2:.2f}", "-i", str(video_path),
              "-frames:v", "1", str(thumb_path)])
        return {"video_path": video_path, "thumb_path": thumb_path, "duration_sec": duration}

    def _segment(self, exe: str, frames: list[Path], dest: Path) -> Path:
        first = Path(frames[0])
        pattern = str(first.parent / (first.stem.rsplit("_", 1)[0] + "_%04d.png"))
        if not list(first.parent.glob(first.stem.rsplit("_", 1)[0] + "_*.png")):
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listed:
                listed.write("".join(f"file '{_q(f)}'\n" for f in frames))
                name = listed.name
            try:
                _run([exe, "-y", "-f", "concat", "-safe", "0", "-i", name,
                      "-framerate", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                      "-r", str(FPS), str(dest)])
            finally:
                _discard(name)
        else:
            _run([exe, "-y", "-framerate", str(FPS), "-i", pattern,
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), str(dest)])
        return dest

    def _concat(self, exe: str, parts: list[Path], dest: Path, stream: str) -> Path:
        del stream  # video-only concat; audio joins separately in _audio_track.
        if len(parts) > 1 and self._xfade(exe, parts, dest):
            return dest
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listed:
            listed.write("".join(f"file '{_q(p)}'\n" for p in parts))
            name = listed.name
        try:
            _run([exe, "-y", "-f", "concat", "-safe", "0", "-i", name,
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), str(dest)])
        finally:
            _discard(name)
        return dest

    def _xfade(self, exe: str, parts: list[Path], dest: Path) -> bool:
        """Join segments with 0.4s crossfades; False means fall back to concat."""
        try:
            durations = [self._probe_duration(exe, p) for p in parts]
        except RuntimeError:
            return False
        if any(d <= FADE_SEC for d in durations):
            return False
        prep = "".join(
            f"[{i}:v]settb=AVTB,fps={FPS},format=yuv420p[v{i}];" for i in range(len(parts))
        )
        running = durations[0]
        prev = "[v0]"
        links: list[str] = []
        for i in range(1, len(parts)):
            out = f"[x{i}]"
            links.append(
                f"{prev}[v{i}]xfade=transition=fade:duration={FADE_SEC}"
                f":offset={running - FADE_SEC:.3f}{out};"
            )
            prev = out
            running += durations[i] - FADE_SEC
        cmd = [exe, "-y"]
        for p in parts:
            cmd += ["-i", str(p)]
        cmd += ["-filter_complex", (prep + "".join(links))[:-1], "-map", prev,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), str(dest)]
        try:
            _run(cmd)
        except RuntimeError:
            return False
        return True

    def _audio_track(self, exe: str, audios: list[Path], out: Path, n_scenes: int) -> Path:
        dest = out / "audio_full.mp3"
        present = [a for a in audios if a.exists()]
        if not present:
            span = max(1.0, n_scenes * 6.0)
            _run([exe, "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={span:.2f}",
                  "-c:a", "libmp3lame", "-b:a", "128k", str(dest)])
            return dest
        silence = out / "pad.mp3"
        _run([exe, "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={PAD_SEC}",
              "-c:a", "libmp3lame", "-b:a", "128k", str(silence)])
        ordered: list[Path] = []
        for i, clip in enumerate(present):
            ordered.append(clip)
            if i < len(present) - 1:
                ordered.append(silence)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listed:
            listed.write("".join(f"file '{_q(p)}'\n" for p in ordered))
            name = listed.name
        try:
            _run([exe, "-y", "-f", "concat", "-safe", "0", "-i", name,
                  "-c:a", "libmp3lame", "-b:a", "128k", str(dest)])
        finally:
            _discard(name)
        return dest

    def _probe_duration(self, exe: str, video: Path) -> float:
        proc = subprocess.run([exe, "-i", str(video)], capture_output=True, text=True, timeout=30)
        info = parse_ffmpeg_info(proc.stderr)
        if info["duration_sec"] is None:
            raise RuntimeError("could not read duration off composed video")
        return info["duration_sec"]
