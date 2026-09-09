"""Invariant tests — 3 topics pass/fail. See docs/06 §6.2."""
from app.concepts.covalent_why import build as build_covalent
from app.concepts.ionic_vs_covalent import build as build_ionic
from app.concepts.ph_scale import build as build_ph
from app.core.models import ConceptId
from app.domain.invariants import check


def test_ph_scale_pass():
    assert check(ConceptId.PH_SCALE, build_ph()) == []


def test_ph_scale_missing_oh_family_fails():
    text = (
        "pH scale 0-14, 7 neutral. Acids sit below pH 7, rich in H+ hydrogen ions. "
        "Bases sit above pH 7 and feel slippery."
    )
    missing = check(ConceptId.PH_SCALE, text)
    assert missing, "expected violations when OH-family is absent"
    assert any("OH" in m for m in missing)


def test_covalent_why_pass():
    assert check(ConceptId.COVALENT_WHY, build_covalent()) == []


def test_covalent_why_missing_electron_fails():
    text = (
        "Two non-metal atoms share a pair to complete the octet, "
        "gaining stability and lower energy."
    )
    missing = check(ConceptId.COVALENT_WHY, text)
    assert missing, "expected violations when electrons are absent"
    assert any("electron" in m for m in missing)


def test_ionic_vs_covalent_pass():
    assert check(ConceptId.IONIC_VS_COVALENT, build_ionic()) == []


def test_ionic_vs_covalent_covalent_only_fails_on_metal_boundary():
    text = (
        "Two non-metal atoms share electrons to form a covalent bond, "
        "reaching a full octet with lower energy and lasting stability."
    )
    missing = check(ConceptId.IONIC_VS_COVALENT, text)
    assert missing, "expected violations for covalent-only text"
    assert any("ionic pair" in m for m in missing)

def test_covalent_why_missing_octet_fails():
    text = (
        "Two non-metal atoms share a pair of electrons, "
        "gaining stability and lower energy together."
    )
    missing = check(ConceptId.COVALENT_WHY, text)
    assert missing, "expected violations when the octet is absent"
    assert any("octet" in m for m in missing)
