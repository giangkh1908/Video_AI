"""Pillow frame renderer — 1280x720 clean-edu diagrams, 24fps PNGs.

One PillowRenderer covers all four visuals (ph-scale-bar gradient,
atom-share circles, compare-table grid, split-screen give-vs-share,
title-card); the subtitle is wrapped FIRST to at most 2 lines and only
then shrunk (never below 28px) so long narrations stay readable; every
drawn string must fit 90% of the canvas (Gate 4 text-overflow rule,
enforced here at draw time, mirrored in QA). Static backgrounds are
cached per visual type and copied per frame so the per-pixel gradient
is painted once per job, not once per frame. A per-scene subtitles.srt
(MoneyPrinter borrow) is written next to the frames so the pipeline
can offset-concat the full subtitles.srt.

The measure helpers (measure_width / fit_font_size / wrap_text /
subtitle_layout) share the exact font metrics used at draw time; QA
imports them lazily to recompute text boxes without a new dependency.
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.models import Scene

WIDTH, HEIGHT, FPS = 1280, 720, 24
BG = (15, 23, 42)
ACCENT = (34, 211, 238)
WHITE = (255, 255, 255)
MUTED = (148, 163, 184)
MAX_W = int(WIDTH * 0.9)

TITLE_SIZE = 54
BULLET_SIZE = 28
SUBTITLE_SIZE = 32
SUBTITLE_FLOOR = 28  # M12: subtitles shrink to fit but never below readable size
PROMPT_SIZE = 28
PROMPT_FLOOR = 22  # takeaway shrinks below the subtitle floor before truncation
TEXT_FLOOR = 12

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_FONT_FILES = (
    str(_ASSETS_DIR / "DejaVuSans-Bold.ttf"),  # vendored (release 2.37); tried first
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
)


def _load_font(size: int):
    for candidate in _FONT_FILES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)  # type: ignore[call-arg]
    except TypeError:
        return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    """textbbox width minus left bearing (bare box[2] overflows on bearing)."""
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int, floor: int = TEXT_FLOOR):
    """Shrink a single line until it fits; floor keeps one readable bound."""
    size = start
    while size > floor:
        font = _load_font(size)
        if _text_width(draw, text, font) <= max_w:
            return font
        size -= 2
    return _load_font(floor)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_w or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if len(lines) > 2:
        # Head line is final; join the tail. (A pop-and-assign loop here
        # re-resolves index -2 after the pop and duplicates content.)
        lines = [lines[0], " ".join(lines[1:])]
    if len(lines) == 2:
        box = draw.textbbox((0, 0), lines[1], font=font)
        while box[2] - box[0] > max_w and len(lines[1]) > 4:
            lines[1] = lines[1][:-2] + "…"
            box = draw.textbbox((0, 0), lines[1], font=font)
    return lines


def _ellipsize(draw: ImageDraw.ImageDraw, line: str, font, max_w: int) -> str:
    box = draw.textbbox((0, 0), line, font=font)
    while box[2] - box[0] > max_w and len(line) > 4:
        line = line[:-2] + "…"
        box = draw.textbbox((0, 0), line, font=font)
    return line


def _subtitle_layout(draw: ImageDraw.ImageDraw, narration: str) -> tuple:
    """Wrap FIRST at full size, shrink only wrapped lines that still overflow.

    Measuring the whole narration on one line before wrapping collapses
    long subtitles to unreadable sizes; wrapping first keeps 32px (down
    to a 28px floor) and ellipsizes only true overflow.
    """
    text = " ".join(narration.split())
    size = SUBTITLE_SIZE
    font = _load_font(size)
    lines = _wrap(draw, text, font, MAX_W)
    while size > SUBTITLE_FLOOR:
        if all(_text_width(draw, line, font) <= MAX_W for line in lines):
            break
        size -= 2
        font = _load_font(size)
        lines = _wrap(draw, text, font, MAX_W)
    return font, [_ellipsize(draw, line, font, MAX_W) for line in lines[:2]]


# --- Shared measure helpers: same metrics as draw time, for QA (lazy import). ---
_measure_draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))


def measure_width(text: str, size: int) -> int:
    """Pixel width of `text` at `size` using the draw-time font chain."""
    box = _measure_draw.textbbox((0, 0), text, font=_load_font(size))
    return box[2] - box[0]


def fit_font_size(text: str, max_w: int, start: int, floor: int = TEXT_FLOOR) -> int:
    """Nominal size the draw-time shrink would settle on for one line."""
    size = start
    while size > floor and measure_width(text, size) > max_w:
        size -= 2
    return size


def wrap_text(text: str, size: int, max_w: int) -> list[str]:
    """Wrap `text` at a fixed size (same rule as draw time)."""
    return _wrap(_measure_draw, text, _load_font(size), max_w)


def subtitle_layout(narration: str) -> tuple[int, list[str]]:
    """Final (size, lines) the renderer burns in for a narration."""
    font, lines = _subtitle_layout(_measure_draw, narration)
    size = getattr(font, "size", SUBTITLE_SIZE)
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = SUBTITLE_SIZE
    return size, lines


def _scene_seed(scene_id: str) -> int:
    """Stable per-scene seed: sha256, never hash() (PYTHONHASHSEED-flaky)."""
    return int.from_bytes(hashlib.sha256(scene_id.encode("utf-8")).digest()[:4], "big")


def format_timestamp(sec: float) -> str:
    total_ms = max(0, int(round(sec * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def write_scene_srt(path: str | Path, index: int, start: float, duration: float, text: str) -> Path:
    out = Path(path)
    out.write_text(
        f"{index + 1}\n"
        f"{format_timestamp(start)} --> {format_timestamp(start + duration)}\n"
        f"{' '.join(text.split())}\n",
        encoding="utf-8",
    )
    return out


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


# --- Static background cache (M19): gradient painted once per visual type. ---
_base_cache: dict[tuple[str, int, int], Image.Image] = {}


def _paint_ph_static(draw: ImageDraw.ImageDraw) -> None:
    x0, x1, y0, y1 = 140, 1140, 300, 360
    stops = [(239, 68, 68), (250, 204, 21), (34, 197, 94), (59, 130, 246), (168, 85, 247)]
    span = x1 - x0
    for x in range(span):
        t = x / span * (len(stops) - 1)
        color = _lerp(stops[int(t)], stops[min(int(t) + 1, len(stops) - 1)], t % 1)
        draw.line([(x0 + x, y0), (x0 + x, y1)], fill=color)
    tick_font = _load_font(22)
    for ph in range(15):
        x = x0 + ph / 14 * span
        draw.line([(x, y1), (x, y1 + 10)], fill=WHITE, width=2)
        draw.text((x, y1 + 26), str(ph), font=tick_font, fill=MUTED, anchor="ma")


def _base_for(visual_type: str) -> Image.Image:
    key = (visual_type, WIDTH, HEIGHT)
    base = _base_cache.get(key)
    if base is None:
        base = Image.new("RGB", (WIDTH, HEIGHT), BG)
        if visual_type == "ph-scale-bar":
            _paint_ph_static(ImageDraw.Draw(base))
        _base_cache[key] = base
    return base.copy()


def _contrasts_ionic_covalent(rows: list[list[str]]) -> bool:
    """A compare-table contrasting both bond kinds earns the split-screen.

    Content-based (not title-based) so template edits that reshape S1/S2
    into contrast tables pick the visual up with no renderer change.
    """
    if len(rows) < 2 or any(len(r) < 3 for r in rows[:2]):
        return False
    first_col = " ".join(r[0] for r in rows).lower()
    return "ionic" in first_col and "covalent" in first_col


KB_ZOOM = 1.10
_KB_W, _KB_H = int(WIDTH * KB_ZOOM), int(HEIGHT * KB_ZOOM)


def _ken_burns(img: Image.Image, progress: float, seed: int) -> Image.Image:
    """Slide a 1280x720 window across a 110% upscale of the finished frame.

    Full-frame (not base-only) so solid-color scenes drift visibly too;
    pan direction alternates per scene from the stable seed. QA-safe: Gate 4
    recomputes text boxes from font metrics, never pixels, and a 90%-fit line
    still sits inside the canvas at 110% (pure Pillow, one resize per frame).
    """
    big = img.resize((_KB_W, _KB_H), Image.BILINEAR)
    travel_x, travel_y = _KB_W - WIDTH, _KB_H - HEIGHT
    leg = progress if seed % 2 == 0 else 1.0 - progress
    x = int(round(travel_x * leg))
    y = int(round(travel_y * leg))
    return big.crop((x, y, x + WIDTH, y + HEIGHT))


class PillowRenderer:
    def render_scene(self, scene: Scene, idx: int, out_dir: Path) -> list[Path]:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        total = max(1, int(round(scene.duration_sec * FPS)))
        paths = []
        for frame in range(total):
            progress = frame / max(1, total - 1)
            path = out / f"scene_{idx:02d}_{frame:04d}.png"
            self._frame(scene, progress).save(path)
            paths.append(path)
        write_scene_srt(out / f"scene_{idx:02d}.srt", idx, 0.0, scene.duration_sec, scene.narration)
        return paths

    def _frame(self, scene: Scene, progress: float) -> Image.Image:
        img = _base_for(scene.visual.type)
        draw = ImageDraw.Draw(img)
        title_font = _fit_font(draw, scene.title, MAX_W, TITLE_SIZE)
        draw.text((WIDTH // 2, 44), scene.title, font=title_font, fill=WHITE, anchor="ma")
        title_bottom = draw.textbbox((WIDTH // 2, 44), scene.title, font=title_font, anchor="ma")[3]
        equation = getattr(scene, "key_equation", None)
        if equation:
            # Measured: title ends ~y107, eq18 at y110 occupies 113..127,
            # bullets at y0=150 start at y139 — 12px clear on both sides.
            eq_font = _fit_font(draw, equation, MAX_W, 18)
            draw.text((WIDTH // 2, 110), equation, font=eq_font, fill=ACCENT, anchor="ma")
        # Bullets start below the equation when present (equation scenes in
        # the templates all have <=2 bullets, clear of visuals at ~y200),
        # otherwise below the measured title bottom (+12px clear).
        bullet_y0 = 150 if equation else max(108, title_bottom + 12)
        for row, bullet in enumerate(scene.bullets[:3]):
            font = _fit_font(draw, bullet, MAX_W, BULLET_SIZE)
            draw.text((140, bullet_y0 + row * 40), f"• {bullet}", font=font, fill=MUTED, anchor="lm")
        visual = scene.visual
        seed = _scene_seed(scene.id)
        jitter = random.Random(seed)
        if visual.type == "ph-scale-bar":
            self._ph_scale(draw, getattr(visual, "highlight", None), progress)
        elif visual.type == "atom-share":
            self._atom_share(draw, getattr(visual, "molecule", "H2"), progress, jitter)
        elif visual.type == "compare-table":
            rows = getattr(visual, "rows", [])
            if _contrasts_ionic_covalent(rows):
                self._split_screen(draw, rows, progress, jitter)
            else:
                self._compare_table(draw, rows)
        else:
            self._title_card(
                draw,
                getattr(visual, "subtitle", None) or scene.title,
                getattr(scene, "learning_objective", None),
            )
        self._subtitle(draw, scene.narration)
        return _ken_burns(img, progress, seed)

    def _ph_scale(self, draw: ImageDraw.ImageDraw, highlight: float | None, progress: float) -> None:
        # Bar + ticks live in the cached base; only the marker moves.
        x0, x1, y0, y1 = 140, 1140, 300, 360
        span = x1 - x0
        marker = highlight if highlight is not None else progress * 14
        mx = x0 + max(0.0, min(14.0, marker)) / 14 * span
        draw.polygon([(mx, y0 - 8), (mx - 14, y0 - 34), (mx + 14, y0 - 34)], fill=WHITE)
        label = _fit_font(draw, "NEUTRAL · pH 7", 300, 26)
        draw.text((x0 + span * 7 / 14, y1 + 58), "NEUTRAL · pH 7", font=label, fill=ACCENT, anchor="ma")

    def _atom_share(self, draw: ImageDraw.ImageDraw, molecule: str, progress: float, jitter: random.Random) -> None:
        for cx in (440, 840):
            draw.ellipse([cx - 110, 220, cx + 110, 440], outline=ACCENT, width=4)
            draw.ellipse([cx - 12, 318, cx + 12, 342], fill=ACCENT)
        label = _fit_font(draw, molecule, 300, 30)
        draw.text((640, 470), molecule, font=label, fill=WHITE, anchor="ma")
        travel = (1.0 - progress) * 130
        for k in range(6):
            side = -1 if k % 2 else 1
            wobble = jitter.uniform(-8, 8)
            draw.ellipse(
                [640 + side * (40 + travel) - 9, 318 + wobble, 640 + side * (40 + travel) + 9, 336 + wobble],
                fill=WHITE,
            )
        draw.ellipse([628, 318, 644, 334], fill=ACCENT)
        draw.ellipse([648, 326, 664, 342], fill=ACCENT)

    def _split_screen(self, draw: ImageDraw.ImageDraw, rows: list[list[str]], progress: float,
                      jitter: random.Random) -> None:
        """Give-vs-share split: ionic transfer left, covalent sharing right.

        Reuses compare-table rows for labels (col 0: bond names, col 2:
        examples) so no new VisualSpec variant is needed.
        """
        left_name = rows[0][0] if len(rows) > 0 else "Ionic bond"
        right_name = rows[1][0] if len(rows) > 1 else "Covalent bond"
        left_ex = rows[0][2] if len(rows) > 0 and len(rows[0]) > 2 else "NaCl salt"
        right_ex = rows[1][2] if len(rows) > 1 and len(rows[1]) > 2 else "H2O water"
        draw.line([(640, 200), (640, 570)], fill=MUTED, width=2)
        header = _fit_font(draw, left_name, 440, 26)
        draw.text((370, 216), left_name, font=header, fill=ACCENT, anchor="ma")
        header = _fit_font(draw, right_name, 440, 26)
        draw.text((910, 216), right_name, font=header, fill=ACCENT, anchor="ma")
        # Left: Na -> Cl transfer resolving to Na+ / Cl- + lattice hint.
        small = _load_font(24)
        for cx, tag, ion in ((270, "Na", "Na+"), (500, "Cl", "Cl-")):
            draw.ellipse([cx - 52, 288, cx + 52, 392], outline=ACCENT, width=4)
            name = _fit_font(draw, tag, 90, 30)
            draw.text((cx, 340), tag, font=name, fill=WHITE, anchor="mm")
            draw.text((cx, 420), ion, font=small, fill=MUTED, anchor="ma")
        tip = 396 + int(progress * 30)
        draw.line([(330, 340), (tip, 340)], fill=WHITE, width=4)
        draw.polygon([(tip, 326), (tip, 354), (tip + 22, 340)], fill=WHITE)
        lattice = _load_font(20)
        for r in range(3):
            for c in range(5):
                draw.text((300 + c * 36, 460 + r * 30), "+-"[(r + c) % 2],
                          font=lattice, fill=MUTED, anchor="mm")
        ex = _fit_font(draw, left_ex, 440, 24)
        draw.text((370, 560), left_ex, font=ex, fill=WHITE, anchor="ma")
        # Right: shared electron pair between two non-metal atoms.
        for cx in (800, 960):
            draw.ellipse([cx - 80, 260, cx + 80, 420], outline=ACCENT, width=4)
        wobble = jitter.uniform(-6, 6)
        draw.ellipse([868, 328 + wobble, 892, 352 + wobble], fill=WHITE)
        draw.ellipse([872 + int(progress * 8), 336 - wobble, 896 + int(progress * 8), 360 - wobble],
                     fill=ACCENT)
        ex = _fit_font(draw, right_ex, 440, 24)
        draw.text((910, 560), right_ex, font=ex, fill=WHITE, anchor="ma")

    def _compare_table(self, draw: ImageDraw.ImageDraw, rows: list[list[str]]) -> None:
        grid = rows or [["MECHANISM", "FORCE", "EXAMPLE"],
                        ["transfer", "lattice", "NaCl"],
                        ["sharing", "covalent", "H2O"]]
        ncols = max(len(r) for r in grid)
        grid = [r + [""] * (ncols - len(r)) for r in grid]
        width = 800 if ncols <= 2 else 1000
        x0, y0 = (WIDTH - width) // 2, 220
        row_h = min(64, 320 // max(1, len(grid)))
        cell = width // ncols
        for r, row in enumerate(grid):
            for c, text in enumerate(row):
                font = _fit_font(draw, text, cell - 24, 24)
                fill = ACCENT if r == 0 else WHITE
                draw.text((x0 + c * cell + cell // 2, y0 + r * row_h + row_h // 2),
                          text, font=font, fill=fill, anchor="mm")
        for r in range(len(grid) + 1):
            draw.line([(x0, y0 + r * row_h), (x0 + width, y0 + r * row_h)], fill=ACCENT, width=2)
        for c in range(ncols + 1):
            draw.line([(x0 + c * cell, y0), (x0 + c * cell, y0 + len(grid) * row_h)], fill=ACCENT, width=2)

    def _title_card(self, draw: ImageDraw.ImageDraw, subtitle: str, prompt: str | None = None) -> None:
        font = _fit_font(draw, subtitle, MAX_W, 44)
        draw.text((WIDTH // 2, 330), subtitle, font=font, fill=ACCENT, anchor="mm")
        if prompt:
            # Shrink first (subtitle pattern, lower floor for the takeaway role);
            # _wrap truncates the tail with "…" so a truncated line means shrink.
            text = " ".join(prompt.split())
            size = PROMPT_SIZE
            prompt_font = _load_font(size)
            lines = _wrap(draw, text, prompt_font, MAX_W)
            while size > PROMPT_FLOOR and any(
                _text_width(draw, line, prompt_font) > MAX_W or line.endswith("…")
                for line in lines
            ):
                size -= 2
                prompt_font = _load_font(size)
                lines = _wrap(draw, text, prompt_font, MAX_W)
            for i, line in enumerate(lines[:2]):
                draw.text((WIDTH // 2, 400 + i * 38), _ellipsize(draw, line, prompt_font, MAX_W),
                          font=prompt_font, fill=WHITE, anchor="ma")

    def _subtitle(self, draw: ImageDraw.ImageDraw, narration: str) -> None:
        font, lines = _subtitle_layout(draw, narration)
        for i, line in enumerate(lines):
            draw.text((WIDTH // 2, 604 + i * 44), line, font=font,
                      fill=WHITE, anchor="ma", stroke_width=2, stroke_fill="black")
