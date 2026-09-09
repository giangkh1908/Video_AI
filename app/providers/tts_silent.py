"""Silent fallback narration — offline 220Hz tone, job still passes.

Used when Edge-TTS fails twice or the box is offline; the pipeline
sets audio_degraded=true and the burned-in subtitles carry the lesson.
Duration matches the Gate 3 estimate (words/2.5 clamped to 5-9s) so
the measured mp3 length agrees with the rendered scene. The tone is
rendered with the imageio-ffmpeg binary via a sine lavfi source —
never array math, never a system install.
"""
import subprocess
import tempfile
from pathlib import Path

WORDS_PER_SEC = 2.5
TONE_HZ = 220


def estimate_duration(text: str) -> float:
    words = len((text or "").split()) or 1
    return min(9.0, max(5.0, words / WORDS_PER_SEC))


class SilentTTS:
    def synthesize(self, text: str, voice: str) -> bytes:
        # voice accepted for TTSProvider shape; a tone has no voice.
        duration = estimate_duration(text)

        from imageio_ffmpeg import get_ffmpeg_exe  # lazy, same rule as edge

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            out = tmp.name
        try:
            subprocess.run(
                [
                    get_ffmpeg_exe(), "-y",
                    "-f", "lavfi",
                    "-i", f"sine=frequency={TONE_HZ}:duration={duration:.2f}",
                    "-c:a", "libmp3lame", "-b:a", "128k",
                    "-ar", "44100", "-ac", "2",
                    out,
                ],
                capture_output=True,
                timeout=30,
                check=True,
            )
            return Path(out).read_bytes()
        except subprocess.SubprocessError as exc:
            raise RuntimeError(f"silent tone render failed: {exc}") from exc
        finally:
            Path(out).unlink(missing_ok=True)
