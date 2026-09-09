"""Provider Protocols — seam between pipeline and generation backends.

The pipeline talks only to these five interfaces, so a real AI
backend (LLM script, ElevenLabs voice, diffusion frames) swaps in by
adding a module under providers/ — never by touching the pipeline.
Pure typing.Protocol; no implementation and no web imports here.
"""
from pathlib import Path
from typing import Protocol

from app.core.models import ConceptId, Scene, ScriptIR


class ScriptProvider(Protocol):
    def generate(self, concept: ConceptId) -> ScriptIR: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str, voice: str) -> bytes: ...


class FrameRenderer(Protocol):
    def render_scene(self, scene: Scene, idx: int, out_dir: Path) -> list[Path]: ...


class Composer(Protocol):
    def compose(
        self,
        frames_by_scene: list[list[Path]],
        audio_paths: list[Path],
        out_dir: Path,
    ) -> dict: ...


class QAGate(Protocol):
    def validate(self, video_path: Path) -> dict: ...
