"""Canonical fallback scripts — 100% curated, always pass Gate 1+2. See docs/06 §6.2.

Last-resort copies are INTENTIONALLY independent literals: they must survive
breakage in app/concepts/*, so this module imports nothing from concepts or
the registry. Each builder constructs a ScriptIR (validated on call), and all
three are built once at import to fail fast if a literal drifts out of spec.
"""
from app.core.models import (
    AtomShare,
    CompareTable,
    ConceptId,
    PhScaleBar,
    Scene,
    ScriptIR,
    TitleCard,
)

__all__ = [
    "build_ph_scale",
    "build_covalent_why",
    "build_ionic_vs_covalent",
    "build_canonical",
]


def build_ph_scale() -> ScriptIR:
    return ScriptIR(
        concept=ConceptId.PH_SCALE,
        title="The pH Scale: Acids, Bases, and Balance",
        scenes=[
            Scene(
                id="s1",
                title="What Is the pH Scale?",
                bullets=["From lemon juice to soap", "One scale explains them all"],
                narration=(
                    "Every liquid hides a secret number, from lemon juice to soap. "
                    "Today we decode the pH scale from zero to fourteen."
                ),
                visual=TitleCard(subtitle="Acids, bases, and the power of 0 to 14"),
                duration_sec=7.0,
                learning_objective="Recall the 0-14 range and the neutral point",
            ),
            Scene(
                id="s2",
                title="A Ruler From 0 to 14",
                bullets=[
                    "0 to 14 covers every solution",
                    "7 is neutral, like pure water",
                    "Each step is 10x stronger",
                ],
                narration=(
                    "The scale runs 0 to 14 for every solution. Seven means neutral, "
                    "like pure water. Each step multiplies strength tenfold."
                ),
                visual=PhScaleBar(highlight=7.0),
                duration_sec=7.0,
            ),
            Scene(
                id="s3",
                title="Acids Give H+, Bases Give OH-",
                bullets=["Acid: pH below 7, rich in H+", "Base: pH above 7, rich in OH-"],
                narration=(
                    "Below pH 7, acids release hydrogen ions known as H+. Above pH 7, "
                    "bases release hydroxide ions known as OH-. At 7, calm neutral water."
                ),
                visual=CompareTable(
                    rows=[
                        ["Acid", "pH below 7", "Rich in H+ ions"],
                        ["Base", "pH above 7", "Rich in OH- ions"],
                        ["Neutral", "pH equals 7", "Balanced H+ and OH-"],
                    ]
                ),
                duration_sec=8.5,
            ),
            Scene(
                id="s4",
                title="Everyday Acids and Bases",
                bullets=["Lemon pH 1-2, stomach acid", "Water pH 7, soap and bleach pH 12-13"],
                narration=(
                    "Lemon juice and stomach acid sit near pH 1 to 2. Water rests at 7. "
                    "Soap and bleach climb to 12 or 13, strong bases."
                ),
                visual=CompareTable(
                    rows=[
                        ["Lemon juice", "pH 1-2", "Acid"],
                        ["Pure water", "pH 7", "Neutral"],
                        ["Soap and bleach", "pH 12-13", "Base"],
                    ]
                ),
                duration_sec=8.5,
            ),
            Scene(
                id="s5",
                title="Quick Check: Where Is Soap?",
                bullets=["Soap feels slippery: acid or base?", "Answer: base, pH 12-13"],
                narration=(
                    "Quick check. Soap feels slippery and bitter. Acid or base, and "
                    "where from 0 to 14? Answer: a base near twelve."
                ),
                visual=TitleCard(subtitle="Pause and predict the pH"),
                duration_sec=7.0,
            ),
        ],
    )


def build_covalent_why() -> ScriptIR:
    return ScriptIR(
        concept=ConceptId.COVALENT_WHY,
        title="Why Atoms Share Electrons",
        scenes=[
            Scene(
                id="s1",
                title="Lonely Atoms Want Full Shells",
                bullets=["Non-metal atoms lack electrons", "Half-empty shells mean high energy"],
                narration=(
                    "Non-metal atoms like hydrogen and oxygen carry half-empty outer "
                    "shells. Those missing electrons leave them restless, unstable, "
                    "and loaded with excess energy."
                ),
                visual=TitleCard(subtitle="Why lonely atoms cannot stay alone"),
                duration_sec=7.5,
                learning_objective="Explain why non-metals share electrons",
            ),
            Scene(
                id="s2",
                title="Sharing: Two Atoms, One Pair",
                bullets=["Electron clouds merge in the middle", "H2: two hydrogen share electrons"],
                narration=(
                    "When two hydrogen atoms meet, their electron clouds merge. They "
                    "share one pair of electrons between them, and both nuclei hold "
                    "that shared pair together."
                ),
                visual=AtomShare(molecule="H2"),
                duration_sec=8.5,
            ),
            Scene(
                id="s3",
                title="Oxygen Shares to Reach Eight",
                bullets=["O2 shares two pairs at once", "Each oxygen counts eight electrons"],
                narration=(
                    "Oxygen needs two more electrons, so two oxygen atoms share two "
                    "pairs. Each atom now counts eight valence electrons, the stable "
                    "octet every non-metal envies."
                ),
                visual=AtomShare(molecule="O2"),
                duration_sec=8.5,
                key_equation="8 valence electrons = stable octet",
            ),
            Scene(
                id="s4",
                title="Sharing Means Lower Energy",
                bullets=["Bonded atoms reach noble-gas calm", "Lower energy means lasting stability"],
                narration=(
                    "Once shared, electrons mimic a noble gas arrangement. The whole "
                    "molecule drops to minimum energy, locking in stability that lone "
                    "atoms can never keep."
                ),
                visual=AtomShare(molecule="H2O"),
                duration_sec=8.0,
            ),
            Scene(
                id="s5",
                title="Quick Check: Why Share?",
                bullets=["Why do non-metals share electrons?", "Answer: full octet, lower energy"],
                narration=(
                    "Final check. Why do non-metal atoms share electrons instead of "
                    "keeping their own? Answer: sharing completes the octet and drops "
                    "the system to lower energy."
                ),
                visual=TitleCard(subtitle="Say it in one sentence"),
                duration_sec=8.5,
            ),
        ],
    )


def build_ionic_vs_covalent() -> ScriptIR:
    return ScriptIR(
        concept=ConceptId.IONIC_VS_COVALENT,
        title="Ionic vs Covalent: Give or Share?",
        scenes=[
            Scene(
                id="s1",
                title="Ionic: A Metal Gives to a Non-Metal",
                bullets=["Sodium gives one electron to chlorine", "Na+ and Cl- lock into salt"],
                narration=(
                    "Meet sodium, a restless metal, and chlorine, a hungry non-metal. "
                    "Sodium donates one electron to chlorine, becoming positive Na+ "
                    "beside negative Cl-."
                ),
                visual=TitleCard(subtitle="When a metal meets a non-metal"),
                duration_sec=7.5,
                learning_objective="Distinguish electron transfer from electron sharing",
            ),
            Scene(
                id="s2",
                title="Covalent: Non-Metals Share",
                bullets=["H2O: hydrogen and oxygen share", "Both non-metal partners hold electrons"],
                narration=(
                    "Now watch water form. Hydrogen and oxygen, both non-metal atoms, "
                    "share electrons instead of giving them away. No ions form; the "
                    "shared pair glues them."
                ),
                visual=AtomShare(molecule="H2O"),
                duration_sec=8.5,
            ),
            Scene(
                id="s3",
                title="Side by Side: Give vs Share",
                bullets=["Left: metal gives to non-metal", "Right: non-metals share together"],
                narration=(
                    "Place them side by side. Ionic means transfer: a metal hands "
                    "electrons to a non-metal. Covalent means sharing: two non-metal "
                    "atoms hold one pair together."
                ),
                visual=CompareTable(
                    rows=[
                        ["Ionic bond", "Electron transfer", "NaCl salt"],
                        ["Covalent bond", "Electron sharing", "H2O water"],
                        ["Partners", "Metal plus non-metal", "Non-metal plus non-metal"],
                    ]
                ),
                duration_sec=8.5,
            ),
            Scene(
                id="s4",
                title="The Full Comparison Matrix",
                bullets=["Mechanism, force, partners, example", "NaCl vs H2O tells the story"],
                narration=(
                    "The matrix seals it. Ionic transfer builds lattices like NaCl from "
                    "a metal plus a non-metal. Covalent sharing builds molecules like "
                    "H2O from two non-metals."
                ),
                visual=CompareTable(
                    rows=[
                        ["Mechanism", "Transfer electrons", "Share electrons"],
                        ["Force", "Ion lattice attraction", "Shared-pair pull"],
                        ["Example", "NaCl: metal plus non-metal", "H2O: both non-metals"],
                    ]
                ),
                duration_sec=8.5,
                key_equation="Na + Cl -> NaCl (transfer) vs H + H -> H2 (sharing)",
            ),
            Scene(
                id="s5",
                title="Quick Check: Salt or Water?",
                bullets=["NaCl forms by transfer or sharing?", "Answer: transfer, metal plus non-metal"],
                narration=(
                    "Last challenge. Salt NaCl forms when sodium meets chlorine. Is that "
                    "electron transfer or electron sharing, and which partners are "
                    "involved? Transfer, metal to non-metal."
                ),
                visual=TitleCard(subtitle="Transfer or sharing — you decide"),
                duration_sec=8.5,
            ),
        ],
    )


def build_canonical(concept: ConceptId) -> ScriptIR:
    """Deterministic fallback for any registered concept (Gate 1 last resort)."""
    builders = {
        ConceptId.PH_SCALE: build_ph_scale,
        ConceptId.COVALENT_WHY: build_covalent_why,
        ConceptId.IONIC_VS_COVALENT: build_ionic_vs_covalent,
    }
    try:
        return builders[concept]()
    except KeyError:
        valid = [c.value for c in builders]
        raise ValueError(f"unsupported concept {concept!r}; expected one of {valid}") from None


# Fail fast at import: every last-resort literal must validate as ScriptIR
# AND pass Gate-2 fact invariants. This is the final fallback path, so a
# literal that loses a keyword must break the deploy, not a 2am job.
def _verify_canonical() -> None:
    from app.domain.invariants import check as _check  # lazy: keep import-time graph core-only

    builders = (
        (ConceptId.PH_SCALE, build_ph_scale),
        (ConceptId.COVALENT_WHY, build_covalent_why),
        (ConceptId.IONIC_VS_COVALENT, build_ionic_vs_covalent),
    )
    for concept, build in builders:
        missing = _check(concept, build())
        if missing:
            raise RuntimeError(f"canonical {concept.value} violates Gate-2 invariants: {missing}")


_verify_canonical()
del _verify_canonical
