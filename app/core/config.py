"""Env config — see docs/08-project-structure.md §8.3."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    artifact_dir: str = os.getenv("ARTIFACT_DIR", "./artifacts")
    script_provider: str = os.getenv("SCRIPT_PROVIDER", "template")  # template | llm
    tts_provider: str = os.getenv("TTS_PROVIDER", "edge")  # edge | silent
    max_workers: int = int(os.getenv("MAX_WORKERS", "2"))
    job_timeout_sec: int = int(os.getenv("JOB_TIMEOUT_SEC", "120"))
    voice: str = os.getenv("VOICE", "en-US-AriaNeural")
    voice_rate: str = os.getenv("VOICE_RATE", "-5%")
    fps: int = int(os.getenv("FPS", "24"))
    width: int = int(os.getenv("WIDTH", "1280"))
    height: int = int(os.getenv("HEIGHT", "720"))
    crossfade_sec: float = float(os.getenv("CROSSFADE_SEC", "0.4"))
    audio_pad_sec: float = float(os.getenv("AUDIO_PAD_SEC", "0.5"))
    scene_min_sec: float = float(os.getenv("SCENE_MIN_SEC", "5"))
    scene_max_sec: float = float(os.getenv("SCENE_MAX_SEC", "9"))
    total_min_sec: float = float(os.getenv("TOTAL_MIN_SEC", "28"))
    total_max_sec: float = float(os.getenv("TOTAL_MAX_SEC", "45"))


settings = Settings()
