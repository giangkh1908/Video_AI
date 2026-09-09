"""ionic-vs-covalent template — curated 5-scene script. See docs/05 §5.5."""
from app.core.models import (
    AtomShare,
    CompareTable,
    ConceptId,
    Scene,
    ScriptIR,
    TitleCard,
)


def build() -> ScriptIR:
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
