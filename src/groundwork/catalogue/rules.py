"""Catalogue rules.

Each rule is a function registered with an id and a default severity. Adding a
check means adding a function — no dispatch table to update, no runner to
change.

Design bias, and it matters: the catalogue only works if adding an entry is a
five-minute job, so these rules are **generous about incompleteness and strict
about silent wrongness**. A thin entry that says "this exists, it's open, it's
LSOA21" should pass. An entry whose boundary vintage contradicts its grain, or
whose references dangle, should not — those are the errors nobody catches by
reading.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from groundwork.findings import Finding, Severity, sort_key, summarise

from groundwork.catalogue.model import (
    GRAIN_VINTAGES,
    REQUIRED_FIELDS,
    VOCABULARIES,
    Catalogue,
)

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNVERIFIED = re.compile(r"NOT verified", re.IGNORECASE)


RuleFn = Callable[[Catalogue], Iterator[Finding]]


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    severity: Severity
    fn: RuleFn


REGISTRY: dict[str, Rule] = {}


def rule(rule_id: str, name: str, severity: Severity = Severity.ERROR):
    def decorator(fn: RuleFn) -> RuleFn:
        if rule_id in REGISTRY:
            raise ValueError(f"Rule {rule_id} already registered")
        REGISTRY[rule_id] = Rule(id=rule_id, name=name, severity=severity, fn=fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


@rule("C001", "unique-ids", Severity.ERROR)
def unique_ids(cat: Catalogue) -> Iterator[Finding]:
    seen: set[str] = set()
    for e in cat.entries:
        if e.id in seen:
            yield Finding("C001", Severity.ERROR, "duplicate id", subject=e.id)
        seen.add(e.id)


@rule("C002", "required-fields", Severity.ERROR)
def required_fields(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        for f in REQUIRED_FIELDS:
            if f not in e.raw:
                yield Finding("C002", Severity.ERROR, "required by the schema", subject=e.id, field=f)


@rule("C003", "id-format", Severity.ERROR)
def id_format(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        if not ID_PATTERN.match(e.id):
            yield Finding(
                "C003", Severity.ERROR,
                "must be a lowercase hyphenated slug",
                subject=e.id, field="id",
            )


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


@rule("V001", "controlled-vocabulary", Severity.ERROR)
def controlled_vocabulary(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        for f, vocab in VOCABULARIES.items():
            value = e.get(f)
            if value is None:
                continue
            if value not in vocab:
                yield Finding(
                    "V001", Severity.ERROR,
                    f"'{value}' is not a recognised value "
                    f"(expected one of {sorted(vocab)}); "
                    f"if it is legitimate, add it to the vocabulary in model.py",
                    subject=e.id, field=f,
                )


# ---------------------------------------------------------------------------
# References and lineage
# ---------------------------------------------------------------------------


@rule("R001", "references-resolve", Severity.ERROR)
def references_resolve(cat: Catalogue) -> Iterator[Finding]:
    known = set(cat.by_id)
    for e in cat.entries:
        for f, target in e.refs():
            if target not in known:
                yield Finding(
                    "R001", Severity.ERROR,
                    f"'{target}' is not an entry in this catalogue — "
                    f"add a historical stub, or fix the reference",
                    subject=e.id, field=f,
                )


@rule("R002", "no-self-reference", Severity.ERROR)
def no_self_reference(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        for f, target in e.refs():
            if target == e.id:
                yield Finding("R002", Severity.ERROR, "refers to itself", subject=e.id, field=f)


@rule("R003", "chain-symmetry", Severity.ERROR)
def chain_symmetry(cat: Catalogue) -> Iterator[Finding]:
    """If A supersedes B then B must be superseded_by A, and vice versa.

    Declared on one side only, this is invisible to a reader and breaks any
    traversal of the release chain.
    """
    by_id = cat.by_id
    for e in cat.entries:
        older = e.get("supersedes")
        if older and older in by_id and by_id[older].get("superseded_by") != e.id:
            yield Finding(
                "R003", Severity.ERROR,
                f"'{older}' does not declare superseded_by: {e.id}",
                subject=e.id, field="supersedes",
            )
        newer = e.get("superseded_by")
        if newer and newer in by_id and by_id[newer].get("supersedes") != e.id:
            yield Finding(
                "R003", Severity.ERROR,
                f"'{newer}' does not declare supersedes: {e.id}",
                subject=e.id, field="superseded_by",
            )


@rule("R004", "chain-terminates", Severity.ERROR)
def chain_terminates(cat: Catalogue) -> Iterator[Finding]:
    by_id = cat.by_id
    for e in cat.entries:
        seen, cur = {e.id}, e
        while cur.get("supersedes"):
            nxt = cur.get("supersedes")
            if nxt not in by_id:
                break  # R001 reports the dangling reference
            if nxt in seen:
                yield Finding(
                    "R004", Severity.ERROR,
                    f"release chain cycles at '{nxt}'",
                    subject=e.id, field="supersedes",
                )
                break
            seen.add(nxt)
            cur = by_id[nxt]


@rule("R005", "incomparability-is-mutual", Severity.WARNING)
def incomparability_is_mutual(cat: Catalogue) -> Iterator[Finding]:
    """If A cannot be compared with B, B cannot be compared with A.

    A warning rather than an error: declaring one direction is genuinely
    useful and forcing both doubles the editing burden. But the missing half
    is worth surfacing, because a consumer checking only B's entry would not
    learn about the incompatibility.
    """
    by_id = cat.by_id
    for e in cat.entries:
        for target in e.not_comparable_ids():
            other = by_id.get(target)
            if other is not None and e.id not in other.not_comparable_ids():
                yield Finding(
                    "R005", Severity.WARNING,
                    f"'{target}' does not declare the reverse incompatibility",
                    subject=e.id, field="not_comparable_with",
                )


# ---------------------------------------------------------------------------
# Semantics — the checks that catch real mistakes
# ---------------------------------------------------------------------------


@rule("S001", "historical-implies-superseded", Severity.ERROR)
def historical_implies_superseded(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        if e.is_historical and not e.get("superseded_by"):
            yield Finding(
                "S001", Severity.ERROR,
                "marked historical but nothing supersedes it",
                subject=e.id, field="historical",
            )


@rule("S002", "grain-vintage-coherent", Severity.ERROR)
def grain_vintage_coherent(cat: Catalogue) -> Iterator[Finding]:
    """An LSOA-grain source on a data zone vintage is a copy-paste error."""
    for e in cat.entries:
        grain, vintage = e.get("grain"), e.get("boundary_vintage")
        allowed = GRAIN_VINTAGES.get(grain)
        if allowed and vintage and vintage not in allowed:
            yield Finding(
                "S002", Severity.ERROR,
                f"grain '{grain}' with boundary_vintage '{vintage}' "
                f"(expected one of {sorted(allowed)})",
                subject=e.id, field="boundary_vintage",
            )


@rule("S003", "geometry-crs-agree", Severity.ERROR)
def geometry_crs_agree(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        geom, crs = e.get("geometry"), e.get("crs")
        if geom and geom != "none" and not crs:
            yield Finding(
                "S003", Severity.ERROR,
                f"geometry is '{geom}' but no crs is declared",
                subject=e.id, field="crs",
            )
        if geom == "none" and crs:
            yield Finding(
                "S003", Severity.ERROR,
                f"geometry is 'none' but crs is '{crs}'",
                subject=e.id, field="crs",
            )


@rule("S004", "restricted-needs-agreement", Severity.WARNING)
def restricted_needs_agreement(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        if e.get("tier") in {"licensed", "restricted"} and not e.get("requires_agreement"):
            yield Finding(
                "S004", Severity.WARNING,
                "tier is not open but no agreement is described — "
                "a prospective user cannot tell what they need",
                subject=e.id, field="requires_agreement",
            )


@rule("S005", "open-tier-redistribution", Severity.WARNING)
def open_tier_redistribution(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        if e.get("tier") == "open" and e.get("redistribution") in {"check-contract", "prohibited"}:
            yield Finding(
                "S005", Severity.WARNING,
                f"tier is 'open' but redistribution is '{e.get('redistribution')}' — "
                "one of the two is wrong",
                subject=e.id, field="redistribution",
            )


@rule("S006", "direct-join-needs-key", Severity.WARNING)
def direct_join_needs_key(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        if e.get("join_via") == "direct" and not e.get("key"):
            yield Finding(
                "S006", Severity.WARNING,
                "join_via is 'direct' but no key column is named",
                subject=e.id, field="key",
            )


@rule("S007", "reviewed-entries-are-verified", Severity.ERROR)
def reviewed_entries_are_verified(cat: Catalogue) -> Iterator[Finding]:
    """An entry cannot claim review while admitting an unverified fact.

    Catches the specific decay where someone marks an entry reviewed without
    clearing the caveats that say otherwise.
    """
    for e in cat.entries:
        if e.get("status") != "reviewed":
            continue
        for caveat in e.get("caveats") or []:
            if UNVERIFIED.search(str(caveat)):
                yield Finding(
                    "S007", Severity.ERROR,
                    "status is 'reviewed' but a caveat still says NOT verified",
                    subject=e.id, field="status",
                )
                break


# ---------------------------------------------------------------------------
# Completeness — advisory only
# ---------------------------------------------------------------------------


@rule("W001", "has-caveats", Severity.WARNING)
def has_caveats(cat: Catalogue) -> Iterator[Finding]:
    """Every source has a gotcha. An entry with none probably has an unwritten one."""
    for e in cat.entries:
        if e.is_historical:
            continue
        if not e.get("caveats"):
            yield Finding(
                "W001", Severity.WARNING,
                "no caveats recorded — this is the field the catalogue exists for",
                subject=e.id, field="caveats",
            )


@rule("W002", "searchable", Severity.WARNING)
def searchable(cat: Catalogue) -> Iterator[Finding]:
    for e in cat.entries:
        if not e.get("keywords"):
            yield Finding("W002", Severity.WARNING, "no keywords — search will miss this", subject=e.id, field="keywords")
        if not e.get("description"):
            yield Finding("W002", Severity.WARNING, "no description", subject=e.id, field="description")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run(cat: Catalogue, *, strict: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for r in REGISTRY.values():
        for f in r.fn(cat):
            findings.append(f.escalated() if strict else f)
    return sorted(findings, key=sort_key)
