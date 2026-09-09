"""Concept registry — add new STEM topic with 1 line. See docs/08 §8.4."""
from collections.abc import Callable

from app.concepts import covalent_why, ionic_vs_covalent, ph_scale
from app.core.models import ConceptId, ScriptIR

CONCEPTS: dict[ConceptId, Callable[[], ScriptIR]] = {
    ConceptId.PH_SCALE: ph_scale.build,
    ConceptId.COVALENT_WHY: covalent_why.build,
    ConceptId.IONIC_VS_COVALENT: ionic_vs_covalent.build,
}


def get(concept: ConceptId) -> Callable[[], ScriptIR]:
    try:
        return CONCEPTS[concept]
    except KeyError:
        valid = [c.value for c in CONCEPTS]
        raise ValueError(f"unsupported concept {concept!r}; expected one of {valid}") from None
