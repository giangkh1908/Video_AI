"""ph-scale template — curated 5-scene script. See docs/05 §5.5."""
from app.core.models import (
    CompareTable,
    ConceptId,
    PhScaleBar,
    Scene,
    ScriptIR,
    TitleCard,
)


def build() -> ScriptIR:
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
