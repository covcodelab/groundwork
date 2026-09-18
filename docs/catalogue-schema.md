# Catalogue schema

**Status:** Draft v0.1
**Purpose:** The shape of a source register entry — enough to find a dataset, judge whether you can use it, and join it correctly, without opening anyone's code.

---

## The modelling decision that shapes everything

**One entry per release, not per dataset.**

`imd-2019` and `imd-2025` are separate entries, not one entry with a version list. They sit on different boundary generations, use different indicators, and are officially not directly comparable. The whole value of this catalogue is that those are different things with different join behaviour, so the schema must not let them share an identity.

Releases are grouped for search by a `dataset` field, and chained by `supersedes` / `superseded_by`.

---

## Fields

### Identity — required

| Field | Notes |
|---|---|
| `id` | Stable slug **including the release**: `imd-2025`, `wimd-2025`. Never reused. |
| `title` | As the publisher names it. |
| `publisher` | The body responsible, not the host. |
| `country` | `england` \| `wales` \| `scotland` \| `northern-ireland` \| `ew` \| `gb` \| `uk`. Load-bearing: deprivation indices are not comparable across nations and a tool that ignores this produces confident nonsense outside England. |
| `url` | A landing page a human can open. |

### Grouping and lineage

| Field | Notes |
|---|---|
| `dataset` | Logical family, for search: `english-indices-of-deprivation`. |
| `description` | One line. |
| `keywords` | Search terms an analyst would actually type. |
| `supersedes` / `superseded_by` | The release chain. `superseded_by: null` means current. |

### Licence and access

| Field | Notes |
|---|---|
| `licence` | `OGL-UK-3.0`, `PSGA`, `commercial`, etc. |
| `tier` | `open` \| `licensed` \| `internal` \| `restricted`. What a borrower needs to know first. |
| `redistribution` | `attribution` \| `derived-only` \| `check-contract` \| `prohibited`. Distinct from `licence` because it is the clause that decides whether a derived value may reach anyone else. |
| `requires_agreement` | Null, or a short description of the agreement needed (PSGA membership, CACI contract, DSA). |
| `access` | `download` \| `api` \| `request` \| `manual`. |
| `resources` | The actually-fetchable things: `{name, url, format}`. |

### Shape — the part that earns the catalogue its keep

| Field | Notes |
|---|---|
| `grain` | `lsoa` \| `data-zone` \| `soa` \| `oa` \| `msoa` \| `uprn` \| `postcode` \| `ward` \| `lad` \| `fra` \| `point`. |
| `boundary_vintage` | `lsoa11` \| `lsoa21` \| `dz11` \| `oa21` \| `uprn` \| `none`. **The single most valuable field in the schema.** |
| `key` | The actual column name(s) you join on, as published. Not "LSOA code" — `LSOA21CD`. |
| `join_via` | `direct` \| `gazetteer` \| `postcode-lookup` \| `best-fit-lookup` \| `spatial`. How you get from this to something else. |
| `geometry` | `none` \| `point` \| `polygon`. |
| `crs` | EPSG code, or null for non-spatial. |
| `formats` | csv, xlsx, geopackage, shapefile, geoparquet, api. |

### Time

| Field | Notes |
|---|---|
| `reference_period` | What period the data *describes*, not when it was published. |
| `reference_period_note` | For heterogeneous cases. IoD 2025 has no single reference date — benefits are March 2024, employment 2022/23, census-derived 2021. |
| `published` | Release date. |
| `update_cadence` | `annual`, `decennial`, `quarterly`, `irregular`, `static`. |

### Judgement — the tribal knowledge

This is what a general data catalogue does not carry and why this one exists.

| Field | Notes |
|---|---|
| `caveats` | Free-text list. The things that cost someone an afternoon to discover. Be specific and be blunt. |
| `comparable_with` | Other `id`s this may safely be compared or joined with. |
| `not_comparable_with` | `{id, reason}`. More useful than `comparable_with`, because the failure is silent. |
| `see_also` | Related entries — the lookup you'll need, the boundary file that goes with it. |

### Historical stubs

Two different ideas, easily conflated:

| | Meaning |
|---|---|
| `superseded_by: <id>` | Not the current release. Says nothing about whether you should use it. |
| `historical: true` | Carried for reference only. Not expected in new work. |

IMD 2019 is superseded and is **not** historical — live models still use it, so it carries a full entry with resources and caveats. IMD 2015 is both, so it gets a stub.

A stub is thin by design: identity, geography, comparability, and whatever caveat stops someone misjoining it. No `resources`, no `access` — nobody should be fetching these routinely. It exists so that `supersedes` chains resolve, and so the boundary vintage of a superseded release is answerable without research.

Rules the checker enforces:

- An entry with `historical: true` must have `superseded_by` set.
- `supersedes` and `superseded_by` must be **symmetric** — if A supersedes B, B is superseded_by A.
- Every chain must terminate in an entry with `supersedes: null`. Where a chain is deliberately cut short, say so in a caveat and why. SIMD stops at 2016 because 2012 used different data zone geographies with no clean lookup.

### Entry provenance

| Field | Notes |
|---|---|
| `status` | `draft` \| `reviewed`. A draft entry has not been checked against the source. |
| `entry_added` / `entry_reviewed` | Dates. |
| `entry_author` | Who to ask. |

---

## What is deliberately absent

**No schema of the data's columns.** Tempting, and it would double the maintenance burden while going stale faster than anything else. Column-level detail belongs to the parser, which fails loudly when it drifts.

**No quality scores or ratings.** Subjective, contestable, and they invite argument rather than use.

**No fetch instructions.** `resources` says where the bytes are. How to get and parse them is the handler's job — config declares the contract, code implements the procedure.

---

## Required minimum

An entry is valid with: `id`, `title`, `publisher`, `country`, `url`, `licence`, `tier`, `grain`, `boundary_vintage`.

Everything else improves it. A thin entry that says "this exists, it's open, it's LSOA21" is still worth more than no entry, and the schema should not make the perfect the enemy of the useful — the catalogue only works if adding an entry is a five-minute job.
