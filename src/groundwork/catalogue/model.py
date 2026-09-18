"""Catalogue loading and controlled vocabularies.

The vocabularies live in code rather than config on purpose: a typo in
`boundary_vintage` is exactly the class of error this catalogue exists to
prevent, so an unrecognised value must fail rather than pass through. Adding
a legitimate new value is a one-line change and the error message says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# --- controlled vocabularies ------------------------------------------------

COUNTRIES = {"england", "wales", "scotland", "northern-ireland", "ew", "gb", "uk"}
TIERS = {"open", "licensed", "internal", "restricted"}
GRAINS = {
    "lsoa",
    "data-zone",
    "soa",
    "oa",
    "msoa",
    "uprn",
    "postcode",
    "ward",
    "lad",
    "fra",
    "point",
}
BOUNDARY_VINTAGES = {
    "lsoa01",
    "lsoa11",
    "lsoa21",
    "dz01",
    "dz11",
    "soa01",
    "soa11",
    "oa01",
    "oa11",
    "oa21",
    "msoa11",
    "msoa21",
    "uprn",
    "none",
    "both",
}
JOIN_VIA = {"direct", "gazetteer", "postcode-lookup", "best-fit-lookup", "spatial"}
GEOMETRIES = {"none", "point", "polygon", "multipolygon"}
REDISTRIBUTION = {"attribution", "permitted", "derived-only", "check-contract", "prohibited"}
ACCESS = {"download", "api", "request", "manual"}
CADENCE = {
    "annual",
    "decennial",
    "quarterly",
    "six-weekly",
    "monthly",
    "continuous",
    "irregular",
    "static",
}
STATUS = {"draft", "reviewed"}

VOCABULARIES: dict[str, set[str]] = {
    "country": COUNTRIES,
    "tier": TIERS,
    "grain": GRAINS,
    "boundary_vintage": BOUNDARY_VINTAGES,
    "join_via": JOIN_VIA,
    "geometry": GEOMETRIES,
    "redistribution": REDISTRIBUTION,
    "access": ACCESS,
    "update_cadence": CADENCE,
    "status": STATUS,
}

REQUIRED_FIELDS = [
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

#: Which boundary vintages are coherent for a given grain. Grains absent from
#: this map are not checked — a postcode file legitimately carries the vintage
#: of whatever geography it maps to, and a rule that is right beats a rule that
#: is comprehensive.
GRAIN_VINTAGES: dict[str, set[str]] = {
    "lsoa": {"lsoa01", "lsoa11", "lsoa21", "both"},
    "data-zone": {"dz01", "dz11", "both"},
    "soa": {"soa01", "soa11", "both"},
    "oa": {"oa01", "oa11", "oa21", "both"},
    "msoa": {"msoa11", "msoa21", "both"},
    "uprn": {"uprn"},
}

REFERENCE_FIELDS = ["see_also", "comparable_with"]
CHAIN_FIELDS = ["supersedes", "superseded_by"]


# --- model ------------------------------------------------------------------


@dataclass
class Entry:
    raw: dict[str, Any]

    def __getattr__(self, name: str) -> Any:
        try:
            return self.raw[name]
        except KeyError:
            raise AttributeError(name) from None

    def get(self, name: str, default: Any = None) -> Any:
        return self.raw.get(name, default)

    @property
    def id(self) -> str:
        return self.raw.get("id", "<no id>")

    @property
    def is_historical(self) -> bool:
        return bool(self.raw.get("historical"))

    def refs(self) -> list[tuple[str, str]]:
        """Every outgoing reference as (field, target_id)."""
        out: list[tuple[str, str]] = []
        for f in REFERENCE_FIELDS:
            for target in self.get(f) or []:
                out.append((f, target))
        for item in self.get("not_comparable_with") or []:
            if isinstance(item, dict) and "id" in item:
                out.append(("not_comparable_with", item["id"]))
        for f in CHAIN_FIELDS:
            target = self.get(f)
            if target:
                out.append((f, target))
        return out

    def not_comparable_ids(self) -> set[str]:
        return {
            i["id"]
            for i in (self.get("not_comparable_with") or [])
            if isinstance(i, dict) and "id" in i
        }


@dataclass
class Catalogue:
    entries: list[Entry] = field(default_factory=list)
    path: Path | None = None

    @property
    def by_id(self) -> dict[str, Entry]:
        return {e.id: e for e in self.entries}

    def __len__(self) -> int:
        return len(self.entries)


class CatalogueLoadError(Exception):
    """The file could not be read as a catalogue at all."""


def load(path: str | Path) -> Catalogue:
    p = Path(path)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CatalogueLoadError(f"{p}: not valid YAML — {exc}") from exc

    if not isinstance(data, dict) or "sources" not in data:
        raise CatalogueLoadError(f"{p}: expected a mapping with a 'sources' key")
    if not isinstance(data["sources"], list):
        raise CatalogueLoadError(f"{p}: 'sources' must be a list")

    return Catalogue(entries=[Entry(raw=e) for e in data["sources"]], path=p)
