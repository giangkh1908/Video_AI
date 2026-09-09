"""LLM script provider — opt-in via SCRIPT_PROVIDER=llm.

EduGen borrow: one system prompt per concept domain plus a JSON-schema
request, so the model returns ScriptIR JSON directly instead of prose.
Gate 1 (strip fences/trailing commas, Pydantic parse, at most 2
retries with backoff 1s/2s carrying the ValidationError back into the
prompt) then Gate 2 (fact invariants). Anything unresolved falls back
to the canonical template; the bool in the returned tuple carries the
fallback_used signal for the pipeline. Stdlib HTTP only.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request

from app.core.models import ConceptId, ScriptIR
from app.domain.invariants import check as invariants_check

MAX_RETRIES = 2
BACKOFFS = (1.0, 2.0)

_SYSTEM_BASE = (
    "You write chemistry micro-lesson scripts for 10th graders. "
    "Return ONLY a single JSON object with keys: concept, title, "
    "scenes (4-6 items, each with id, title max 60 chars, bullets 1-3 "
    "of max 80 chars, narration 20-60 words, visual, duration_sec 5-9), "
    "style ('clean-edu'). Total duration must be 28-45s. "
    "Visual is one of: {\"type\":\"ph-scale-bar\",\"highlight\":7} | "
    "{\"type\":\"atom-share\",\"molecule\":\"H2\"} | "
    "{\"type\":\"compare-table\",\"rows\":[[\"a\",\"b\"]]} | "
    "{\"type\":\"title-card\",\"subtitle\":\"...\"}. No markdown, no commentary."
)
SYSTEM_PROMPTS = {
    ConceptId.PH_SCALE: (
        _SYSTEM_BASE
        + " Concept 'ph-scale': narration+bullets MUST mention the 0-14 range, "
        "neutral 7, acid below 7, base/alkaline above 7, and H+/hydrogen or "
        "OH-/hydroxide ions, with everyday examples (lemon, water, soap)."
    ),
    ConceptId.COVALENT_WHY: (
        _SYSTEM_BASE
        + " Concept 'covalent-why': narration+bullets MUST mention shared/sharing "
        "electrons, the octet (or 8 electrons), non-metal atoms, and stability "
        "or lower energy, e.g. H2/O2 reaching a noble-gas configuration."
    ),
    ConceptId.IONIC_VS_COVALENT: (
        _SYSTEM_BASE
        + " Concept 'ionic-vs-covalent': narration+bullets MUST contrast transfer "
        "(donate/give-take, cation/anion) with sharing, metal plus non-metal "
        "(ionic, e.g. NaCl) versus non-metal plus non-metal (covalent, e.g. H2O)."
    ),
}


def _strip_fences(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    return match.group(1).strip() if match else raw.strip()


def _strip_trailing_commas(raw: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", raw)


def _parse_script(raw: str) -> ScriptIR:
    cleaned = _strip_trailing_commas(_strip_fences(raw))
    return ScriptIR.model_validate(json.loads(cleaned))


def _script_text(script: ScriptIR) -> str:
    # Gate-2 scope is narration+bullets ONLY (no title) — same join as
    # services/pipeline.py, so a fact stuffed into a title cannot pass here
    # and get rejected (or slip through) at runtime.
    return " ".join(f"{' '.join(s.bullets)} {s.narration}" for s in script.scenes)


def _post_chat(api_url: str, api_key: str, model: str, system: str, user: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return str(payload)


def _user_prompt(concept: ConceptId, errors: str) -> str:
    prompt = f'Write the script for concept "{concept.value}".'
    if errors:
        prompt += f" The previous output was rejected: {errors} Fix it and return valid JSON only."
    return prompt


class LLMScriptProvider:
    def __init__(self, api_url: str = "", api_key: str = "", model: str = "") -> None:
        self.api_url = api_url or os.getenv("LLM_API_URL", "")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    def generate(self, concept: ConceptId) -> tuple[ScriptIR, bool]:
        if not self.api_url or not self.api_key:
            return self._fallback(concept), True
        system = SYSTEM_PROMPTS[concept]
        errors = ""
        raw = ""
        for attempt in range(MAX_RETRIES + 1):
            if attempt:
                time.sleep(BACKOFFS[min(attempt - 1, len(BACKOFFS) - 1)])
            try:
                raw = _post_chat(
                    self.api_url, self.api_key, self.model,
                    system, _user_prompt(concept, errors),
                )
            except Exception as exc:
                errors = f"HTTP call failed ({exc}); return the JSON schema described."
                continue
            try:
                script = _parse_script(raw)
            except Exception as exc:
                errors = f"schema validation failed: {exc}. Return corrected JSON only."
                continue
            missing = invariants_check(concept, _script_text(script))
            if missing:
                errors = f"fact invariants missing ({', '.join(missing)}); rewrite to include them."
                continue
            return script, False
        return self._fallback(concept), True

    def _fallback(self, concept: ConceptId) -> ScriptIR:
        from app.domain import canonical_templates as canonical

        builders = {
            ConceptId.PH_SCALE: "build_ph_scale",
            ConceptId.COVALENT_WHY: "build_covalent_why",
            ConceptId.IONIC_VS_COVALENT: "build_ionic_vs_covalent",
        }
        build = getattr(canonical, builders[concept], None)
        if build is None:
            raise RuntimeError(f"canonical fallback unavailable for {concept.value}")
        return build()
