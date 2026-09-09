"""Edge-TTS narration — default voice provider, free tier.

Voice and rate come from TTS_VOICE / TTS_RATE env (defaults
en-US-AriaNeural at -5%). Results are cached by sha1(narration+voice)
in memory and under TTS_CACHE_DIR so repeat requests cost nothing.
Any failure raises RuntimeError; the pipeline, not this module,
decides the SilentTTS fallback.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path

DEFAULT_VOICE = "en-US-AriaNeural"

_cache: dict[str, bytes] = {}


def _cache_dir() -> Path:
    root = Path(os.getenv("TTS_CACHE_DIR", "./artifacts/.tts_cache"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cache_path(digest: str) -> Path:
    return _cache_dir() / f"{digest}.mp3"


class EdgeTTSProvider:
    def __init__(self, voice: str = "", rate: str = "") -> None:
        self.voice = voice or os.getenv("TTS_VOICE", DEFAULT_VOICE)
        self.rate = rate or os.getenv("TTS_RATE", "-5%")

    def synthesize(self, text: str, voice: str) -> bytes:
        if not text or not text.strip():
            raise ValueError("empty narration text")
        active = voice or self.voice
        digest = hashlib.sha1(f"{text}\x00{active}".encode()).hexdigest()
        if digest in _cache:
            return _cache[digest]
        cached_file = _cache_path(digest)
        if cached_file.exists():
            data = cached_file.read_bytes()
            _cache[digest] = data
            return data
        data = asyncio.run(self._fetch(text, active, self.rate))
        _cache[digest] = data
        try:
            # Atomic publish: concurrent jobs sharing one cache path must
            # never observe a half-written mp3, and on Windows a direct
            # write_bytes race raises PermissionError. A unique tmp file +
            # os.replace keeps the swap atomic; failure only skips the
            # on-disk cache — the fetched bytes below are still returned.
            fd, tmp_name = tempfile.mkstemp(
                dir=cached_file.parent, prefix=f"{digest[:12]}-", suffix=".mp3.tmp"
            )
            try:
                with os.fdopen(fd, "wb") as tmp:
                    tmp.write(data)
                os.replace(tmp_name, cached_file)
            except OSError:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
        except OSError:
            pass
        return data

    async def _fetch(self, text: str, voice: str, rate: str) -> bytes:
        import edge_tts  # lazy: keeps module importable without the lib

        # One unique file per call: synthesize runs on pool threads and the
        # old shared tmp-{pid} name let a job unlink another's audio mid-read.
        fd, name = tempfile.mkstemp(prefix="edge-", suffix=".mp3", dir=_cache_dir())
        os.close(fd)
        tmp = Path(name)
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(str(tmp))
            return tmp.read_bytes()
        except Exception as exc:
            raise RuntimeError(f"edge tts failed: {exc}") from exc
        finally:
            tmp.unlink(missing_ok=True)
