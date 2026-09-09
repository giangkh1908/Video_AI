"""Fact invariants — Gate 2 rules. See docs/06 §6.2."""
import re

from app.core.models import ConceptId, ScriptIR


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _text_of(script: ScriptIR | str) -> str:
    if isinstance(script, str):
        return script
    parts: list[str] = []
    for scene in script.scenes:
        parts.append(scene.narration)
        parts.extend(scene.bullets)
    return "\n".join(parts)


def check(concept: ConceptId, script: ScriptIR | str) -> list[str]:
    """Gate 2 fact gate, case-insensitive over narration+bullets join.

    Returns violation strings; empty list means the script passes.
    """
    text = _text_of(script)
    if concept == ConceptId.PH_SCALE:
        return _check_ph_scale(text)
    if concept == ConceptId.COVALENT_WHY:
        return _check_covalent_why(text)
    if concept == ConceptId.IONIC_VS_COVALENT:
        return _check_ionic_vs_covalent(text)
    raise ValueError(f"unsupported concept {concept!r}")


def _check_ph_scale(text: str) -> list[str]:
    missing: list[str] = []
    if not _has(text, r"0\s*[-\u2013\u2014]\s*14", r"0\s+to\s+14"):
        missing.append("ph-scale: missing range token 0-14")
    if not _has(text, r"\b7\b", r"neutral"):
        missing.append("ph-scale: missing neutral marker (7 or neutral)")
    if not _has(text, r"acid", r"ph\s*<\s*7", r"<\s*7", r"below\s+7", r"under\s+7"):
        missing.append("ph-scale: missing acid side (acid / pH below 7)")
    if not _has(text, r"base", r"basic", r"alkaline", r"ph\s*>\s*7", r">\s*7", r"above\s+7"):
        missing.append("ph-scale: missing base side (base / alkaline / pH above 7)")
    if not _has(text, r"H\+", r"H\uff0b", r"hydrogen"):
        missing.append("ph-scale: missing H-family (H+ / hydrogen)")
    if not _has(text, r"OH-", r"OH\u2212", r"hydroxide"):
        missing.append("ph-scale: missing OH-family (OH- / hydroxide)")
    return missing


def _check_covalent_why(text: str) -> list[str]:
    missing: list[str] = []
    if not _has(text, r"shar\w*"):
        missing.append("covalent-why: missing sharing (share/shared/sharing)")
    if not _has(text, r"electron\w*"):
        missing.append("covalent-why: missing electrons")
    if not _has(text, r"non-?metals?\b"):
        missing.append("covalent-why: missing non-metal")
    if not _has(text, r"stab\w*", r"energ\w*"):
        missing.append("covalent-why: missing stability/energy")
    if not _has(text, r"octet", r"8\s*electrons?", r"eight\s+electrons?"):
        missing.append("covalent-why: missing octet (octet / 8 electrons)")
    return missing


def _check_ionic_vs_covalent(text: str) -> list[str]:
    missing: list[str] = []
    if not _has(
        text,
        r"transfer\w*",
        r"donat\w*",
        r"giv\w*[^.\n]{0,60}take\w*",
        r"cation",
        r"anion",
    ):
        missing.append("ionic-vs-covalent: missing transfer (transfer/donate/cation-anion)")
    if not _has(text, r"shar\w*"):
        missing.append("ionic-vs-covalent: missing sharing")
    ionic_metal = _has(text, r"(?<!non-)\bmetals?\b")
    has_nonmetal = _has(text, r"non-?metals?\b")
    if not (ionic_metal and has_nonmetal):
        missing.append("ionic-vs-covalent: missing ionic pair (metal + non-metal)")
    pair_count = len(re.findall(r"non-?metals?\b", text, re.IGNORECASE))
    if pair_count < 2 and not _has(text, r"both\s+non-?metals?"):
        missing.append("ionic-vs-covalent: missing covalent pair (non-metal + non-metal)")
    return missing
