"""covalent-why template — curated 5-scene script. See docs/05 §5.5."""
from app.core.models import (
    AtomShare,
    ConceptId,
    Scene,
    ScriptIR,
    TitleCard,
)


def build() -> ScriptIR:
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
