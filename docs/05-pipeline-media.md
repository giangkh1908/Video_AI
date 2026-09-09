# 05 — Generation Pipeline & Media Spec

## 5.1 Pipeline 5 stages (`services/pipeline.py :: run_pipeline(job_id)`)

| Stage | In → Out | Provider | Thời gian | Progress |
|---|---|---|---|---|
| 1. Scripting | concept → ScriptIR | ScriptProvider | 0.1s (template) / ~3s (LLM) | 0→20 |
| 2. Narrating | ScriptIR → audio per scene | TTSProvider | ~8s | 20→40 |
| 3. Rendering | ScriptIR → frames PNG | FrameRenderer | ~5s | 40→75 |
| 4. Compositing | frames+audio → video.mp4 + thumb.jpg (frame giữa) | Composer (ffmpeg) | ~5s | 75→90 |
| 5. Validating | video.mp4 → pass/fail | QAGate | ~1s | 90→100 |

Mỗi stage: `set_status() → làm → save timings → update progress`. Throw → catch tại pipeline → `FAILED + ErrorInfo`, không kẹt.

## 5.2 Providers

```python
# providers/base.py — Protocols, không implementation
class ScriptProvider(Protocol):
    def generate(self, concept: ConceptId) -> ScriptIR: ...
class TTSProvider(Protocol):
    def synthesize(self, text: str, voice: str) -> bytes: ...   # mp3 bytes
class FrameRenderer(Protocol):
    def render_scene(self, scene: Scene, idx: int, out_dir: Path) -> list[Path]: ...
class Composer(Protocol):
    def compose(self, frames_by_scene: dict[str, list[Path]], audio_paths: list[Path], out_dir: Path) -> dict: ...   # {video_path, thumb_path, duration_sec}
class QAGate(Protocol):
    def validate(self, video_path: Path) -> dict: ...   # {passed, checks}
```

- **Script:** default `TemplateScriptProvider` (đọc `concepts/*.py`, curated tay). Opt-in `LLMScriptProvider` qua `SCRIPT_PROVIDER=llm` (gọi API, parse, qua Gate 1+2, fail → fallback template).
- **TTS:** default `EdgeTTSProvider` (`en-US-AriaNeural`, rate -5%). Fail 2 lần/offline → `SilentTTS` (sine 220Hz + giữ subtitle), flag `audio_degraded=true`. Cache theo `sha1(narration+voice)` để request trùng không tốn TTS.
- **Render:** `PillowRenderer` duy nhất. Không matplotlib/SVG lẫn lộn.
- **Composer:** binary ffmpeg lấy qua `imageio_ffmpeg.get_ffmpeg_exe()` + ffmpeg concat, crossfade 0.4s, AAC audio, H.264 MP4, pad silence 0.3s giữa scenes. Không yêu cầu cài ffmpeg hệ thống. Composer không gọi ffprobe; Gate 3/4 đo duration/audio-stream bằng mutagen + `ffmpeg -i` parse (không cần ffprobe hệ thống).

## 5.3 Visual spec (chốt)

Canvas 1280x720, nền `#0F172A`, accent `#22D3EE`, text trắng, font DejaVu Sans Bold (bundle, không phụ thuộc font hệ thống). Subtitle trắng viền đen dưới, max 2 dòng. Motion: crossfade + Ken Burns zoom nhẹ + marker di chuyển (đủ feel video, rẻ).

- **ph-scale / PhScaleBar:** thanh gradient đỏ→vàng→xanh lá→lam→tím full width, ticks 0–14, marker tam giác chạy, highlight pH 7 "NEUTRAL". Cards ví dụ: chanh/dạ dày 1-2, nước 7, xà phòng/tẩy 12-13.
- **covalent-why / AtomShare:** 2 vòng tròn nguyên tử + electron dots; animation dots di chuyển vào giữa thành shared pair; mũi tên năng lượng đi xuống; callout octet cho O2/H2O.
- **ionic-vs-covalent / CompareTable:** split-screen trái Na→Cl (mũi tên bay hẳn sang, hiện Na+/Cl- + lattice) / phải H–H (electron ở giữa); bảng cuối 4 rows: mechanism, force, elements, example (NaCl vs H2O).
- **TitleCard:** layout title + subtitle giữa canvas, params `subtitle?`, dùng cho S1 Hook và S5 quiz.

## 5.4 Audio spec

- Voice default `en-US-AriaNeural`, rate `-5%`, ~2.5 words/s.
- Per-scene mp3 → concat → `audio_full.mp3`. Scene duration cuối = `clamp(audio_sec + 0.5, 5, 9)`.
- Nếu TTS vắng mặt: vẫn render video với subtitle + tone, không fail job.
- Tổng 28–45s; `est_audio = words/2.5` phải nằm trong `duration ±2s`, lệch → auto-stretch duration (warn trong log).

## 5.5 Storyboards (5 scenes, từ agy chuẩn hóa duration)

1. **ph-scale:** S1 Hook title → S2 scale 0–14 + marker → S3 acid (H+, <7) vs base (OH-, >7) + log 10x → S4 examples (chanh/dạ dày 1-2, nước 7, xà phòng/tẩy 12-13) → S5 quiz.
2. **covalent-why:** S1 problem (non-metal thiếu e, năng lượng cao) → S2 sharing (mây e hòa vào nhau, H2/O2) → S3 octet → S4 outcome (khí hiếm, E cực tiểu) → S5 quiz.
3. **ionic-vs-covalent:** S1 ionic (transfer cho-nhận, metal+non-metal, NaCl) → S2 covalent (non-metal+non-metal, H2O/CO2) → S3 split-screen → S4 matrix → S5 quiz.

Mỗi scene: title ≤60 chars, 1–3 bullets ≤80 chars, narration 20–60 words bám fact invariants (§06).
- Scene có thêm 2 field optional (borrow EduGen): `key_equation: str | None`, `learning_objective: str | None` — render callout khi có, không bắt buộc.
- Per-scene `subtitles.srt` sinh từ narration + duration cuối (borrow MoneyPrinter): concat thành `subtitles.srt` per job, burn-in tối đa 2 dòng khi render.
