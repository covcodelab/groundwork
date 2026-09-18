"""Each test breaks the catalogue in one specific way and asserts the rule fires.

A checker nobody has watched fail is not a checker. These tests exist so that
every rule has been seen to catch the thing it claims to catch.
"""

from __future__ import annotations

import copy

import pytest

from groundwork.catalogue.model import Catalogue, Entry
from groundwork.catalogue.rules import REGISTRY, run
from groundwork.findings import Severity

BASE = {
    "id": "example-2025",
    "title": "Example dataset 2025",
    "publisher": "Example Publisher",
    "country": "england",
    "url": "https://example.org/",
    "licence": "OGL-UK-3.0",
    "tier": "open",
    "grain": "lsoa",
    "boundary_vintage": "lsoa21",
    "key": "LSOA21CD",
    "join_via": "direct",
    "geometry": "none",
    "crs": None,
    "description": "An example.",
    "keywords": ["example"],
    "caveats": ["Something that would cost you an afternoon."],
    "status": "draft",
}


def cat(*entries: dict) -> Catalogue:
    return Catalogue(entries=[Entry(raw=copy.deepcopy(e)) for e in entries])


def rules_fired(findings) -> set[str]:
    return {f.rule for f in findings}


def test_a_well_formed_entry_passes_cleanly():
    findings = run(cat(BASE))
    assert findings == [], [str(f) for f in findings]


def test_a_thin_entry_still_passes_without_errors():
    """Generous about incompleteness: the catalogue only works if adding an
    entry is a five-minute job."""
    thin = {
        k: BASE[k]
        for k in [
            "id",
            "title",
            "publisher",
            "country",
            "url",
            "licence",
            "tier",
            "grain",
            "boundary_vintage",
        ]
    }
    findings = run(cat(thin))
    assert not [f for f in findings if f.severity is Severity.ERROR]
    assert {"W001", "W002"} <= rules_fired(findings)


# --- structure --------------------------------------------------------------


def test_duplicate_ids_are_caught():
    assert "C001" in rules_fired(run(cat(BASE, BASE)))


def test_missing_required_field_is_caught():
    broken = {k: v for k, v in BASE.items() if k != "boundary_vintage"}
    assert "C002" in rules_fired(run(cat(broken)))


@pytest.mark.parametrize("bad_id", ["Example_2025", "example 2025", "EXAMPLE", "-leading"])
def test_bad_id_format_is_caught(bad_id):
    assert "C003" in rules_fired(run(cat({**BASE, "id": bad_id})))


# --- vocabulary -------------------------------------------------------------


def test_unknown_vocabulary_value_is_caught():
    findings = run(cat({**BASE, "boundary_vintage": "lsoa2021"}))
    assert "V001" in rules_fired(findings)


def test_vocabulary_error_names_the_alternatives():
    findings = run(cat({**BASE, "tier": "publicish"}))
    msg = next(f.message for f in findings if f.rule == "V001")
    assert "open" in msg and "licensed" in msg


# --- references and lineage -------------------------------------------------


def test_dangling_reference_is_caught():
    assert "R001" in rules_fired(run(cat({**BASE, "see_also": ["does-not-exist"]})))


def test_dangling_supersedes_suggests_a_stub():
    findings = run(cat({**BASE, "supersedes": "example-2019"}))
    msg = next(f.message for f in findings if f.rule == "R001")
    assert "historical stub" in msg


def test_self_reference_is_caught():
    assert "R002" in rules_fired(run(cat({**BASE, "see_also": ["example-2025"]})))


def test_one_sided_chain_link_is_caught():
    """The bug that was actually in the catalogue and invisible to a reader."""
    old = {**BASE, "id": "example-2019", "boundary_vintage": "lsoa11", "key": "LSOA11CD"}
    new = {**BASE, "supersedes": "example-2019"}
    findings = run(cat(old, new))
    assert "R003" in rules_fired(findings)


def test_symmetric_chain_passes():
    old = {
        **BASE,
        "id": "example-2019",
        "boundary_vintage": "lsoa11",
        "key": "LSOA11CD",
        "superseded_by": "example-2025",
    }
    new = {**BASE, "supersedes": "example-2019"}
    assert not [f for f in run(cat(old, new)) if f.severity is Severity.ERROR]


def test_cyclic_chain_is_caught():
    a = {**BASE, "id": "a-2020", "supersedes": "b-2020", "superseded_by": "b-2020"}
    b = {**BASE, "id": "b-2020", "supersedes": "a-2020", "superseded_by": "a-2020"}
    assert "R004" in rules_fired(run(cat(a, b)))


def test_one_sided_incomparability_warns_but_does_not_fail():
    a = {
        **BASE,
        "id": "a-2020",
        "not_comparable_with": [{"id": "b-2020", "reason": "different index"}],
    }
    b = {**BASE, "id": "b-2020"}
    findings = run(cat(a, b))
    assert "R005" in rules_fired(findings)
    assert not [f for f in findings if f.severity is Severity.ERROR]


# --- semantics --------------------------------------------------------------


def test_historical_without_successor_is_caught():
    assert "S001" in rules_fired(run(cat({**BASE, "historical": True})))


def test_grain_and_vintage_mismatch_is_caught():
    """An LSOA source on a Scottish data zone vintage is a copy-paste error."""
    findings = run(cat({**BASE, "grain": "lsoa", "boundary_vintage": "dz11"}))
    assert "S002" in rules_fired(findings)


def test_postcode_grain_is_not_vintage_checked():
    """A postcode file legitimately carries the vintage of what it maps to."""
    entry = {
        **BASE,
        "grain": "postcode",
        "boundary_vintage": "lsoa21",
        "key": "pcds",
        "join_via": "postcode-lookup",
    }
    assert "S002" not in rules_fired(run(cat(entry)))


def test_geometry_without_crs_is_caught():
    entry = {**BASE, "geometry": "polygon", "crs": None}
    assert "S003" in rules_fired(run(cat(entry)))


def test_crs_without_geometry_is_caught():
    entry = {**BASE, "geometry": "none", "crs": "EPSG:27700"}
    assert "S003" in rules_fired(run(cat(entry)))


def test_licensed_without_agreement_warns():
    entry = {**BASE, "tier": "licensed", "redistribution": "check-contract"}
    findings = run(cat(entry))
    assert "S004" in rules_fired(findings)
    assert not [f for f in findings if f.severity is Severity.ERROR]


def test_open_tier_with_restrictive_redistribution_warns():
    entry = {**BASE, "tier": "open", "redistribution": "prohibited"}
    assert "S005" in rules_fired(run(cat(entry)))


def test_direct_join_without_key_warns():
    entry = {k: v for k, v in BASE.items() if k != "key"}
    assert "S006" in rules_fired(run(cat(entry)))


def test_reviewed_entry_admitting_an_unverified_fact_is_caught():
    entry = {
        **BASE,
        "status": "reviewed",
        "caveats": ["Boundary vintage stated here is NOT verified."],
    }
    assert "S007" in rules_fired(run(cat(entry)))


def test_reviewed_entry_with_clean_caveats_passes():
    entry = {**BASE, "status": "reviewed", "caveats": ["Verified 17 Sep 2026."]}
    assert "S007" not in rules_fired(run(cat(entry)))


# --- runner behaviour -------------------------------------------------------


def test_strict_promotes_warnings_to_errors():
    entry = {k: v for k, v in BASE.items() if k != "caveats"}
    assert not [f for f in run(cat(entry)) if f.severity is Severity.ERROR]
    assert [f for f in run(cat(entry), strict=True) if f.severity is Severity.ERROR]


def test_errors_sort_before_warnings():
    entry = {**BASE, "id": "Bad_Id"}
    del entry["caveats"]
    severities = [f.severity for f in run(cat(entry))]
    assert severities == sorted(severities, key=lambda s: s is not Severity.ERROR)


def test_every_registered_rule_has_a_test():
    """Guards against a rule being added without anyone watching it fire."""
    import pathlib

    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    untested = [rid for rid in REGISTRY if rid not in source]
    assert not untested, f"rules with no test: {untested}"
