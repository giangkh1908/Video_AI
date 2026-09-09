"""Template script provider — deterministic default, works offline.

Reads the curated per-concept builders out of concepts/registry.py.
The import stays inside the method so providers never create an
import cycle with the concept modules at load time.
"""
from app.core.models import ConceptId, ScriptIR


class TemplateScriptProvider:
    def generate(self, concept: ConceptId) -> ScriptIR:
        from app.concepts import registry

        try:
            builder = registry.CONCEPTS[concept]
        except KeyError:
            raise ValueError(f"unsupported concept: {concept}") from None
        build = getattr(builder, "build", builder)
        try:
            return build()  # type: ignore[operator]
        except TypeError:
            return build(concept)  # type: ignore[operator]
