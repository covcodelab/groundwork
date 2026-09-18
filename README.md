# groundwork

**Find, acquire and prepare UK public geodata — without rediscovering the same gotchas every time.**

Status: early. The catalogue is real and checked; the fetch and conform pieces are not built yet.

---

## The problem

Getting to the point where you can do the analysis costs more time than the analysis. Data has to be found across half a dozen portals, checked for vintage, reprojected, matched to a gazetteer, and joined across geographies that do not align — and much of it is redone the next time the question shifts or a source refreshes.

Most of that cost is **knowledge**, not code. data.gov.uk will tell you the English Indices of Deprivation exist. It will not tell you that IoD 2025 sits on 2021 LSOA boundaries while IoD 2019 sits on 2011 boundaries, that joining either to the wrong census generation is silently wrong, or which lookup mediates between them.

That knowledge is what this catalogue carries.

## Three pieces

| Piece | Does | State |
|---|---|---|
| **The catalogue** | What exists, at what grain, on which boundary vintage, under what licence, with what gotchas | **Usable now** |
| **The conformer** | A source table into canonical form — EPSG:27700, stamped keys, typed columns | Not built |
| **The checker** | A data file against expectations | Not built |

Each is meant to be useful on its own. The catalogue answers questions without fetching a byte; the conformer works on a table you got any way you liked; the checker runs on anyone's file, including ones this tool never touched.

## Try it

```bash
uv sync
uv run catcheck catalogue.yaml       # check the catalogue
uv run catcheck --rules              # what the 18 rules catch
```

Then read [`catalogue.yaml`](catalogue.yaml). Twenty-five entries covering the working set for UK small-area analysis — four nations, four mutually incomparable deprivation indices, the boundary generations, the lookups that make joins legal, and the licensed sources you may not be able to reach.

## What the catalogue is for

An entry answers three questions in about a minute, without opening anyone's code:

- **Can I get this?** Licence, tier, what agreement it needs.
- **Does it join to what I have?** Grain, boundary vintage, key column, join route.
- **What will bite me?** Caveats, and what this is explicitly *not* comparable with.

The third field is the one a general data catalogue does not carry, and it is why this one exists.

## The catalogue is data

`catalogue.yaml` is a plain file. Adding an entry is a five-minute pull request against a data file — no Python required, no build to understand. That is deliberate: a catalogue that only maintainers can extend does not get extended.

The checker enforces the things that cause silent wrongness (dangling references, a grain that contradicts its boundary vintage, an entry claiming review while admitting an unverified fact) and merely warns about incompleteness. A thin entry that says "this exists, it's open, it's LSOA21" passes.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Documentation

| | |
|---|---|
| [`docs/catalogue-schema.md`](docs/catalogue-schema.md) | Every field and why it earns its place |
| [`docs/vintages.md`](docs/vintages.md) | Boundary generations, index releases, and how to join across them without lying |
| [`docs/history.md`](docs/history.md) | Where this came from, and what was deliberately left behind |

## Scope

**In:** discovery, acquisition, preparation. Files on disk. What you do with them is your business.

**Out:** orchestration, models, dashboards, serving infrastructure, governance. Those were all tried in an earlier design and cut — see [`docs/history.md`](docs/history.md).

## Data policy

**No licensed or personal data in this repository, on any branch, ever.** The catalogue describes licensed sources; it never contains them. `.gitignore` blocks common data formats as a safety net, not as a control.

## Licence

MIT — see [`LICENSE`](LICENSE).

---

*CovCodeLab*
