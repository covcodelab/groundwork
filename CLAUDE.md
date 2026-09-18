# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A catalogue of UK public geodata sources (`catalogue.yaml`) plus `catcheck`, a rule-based checker for it. The catalogue carries the knowledge a generic data portal does not: boundary vintage, join route, licence tier, and the gotchas ("caveats") that make joins silently wrong. Two further pieces — a conformer (source table → EPSG:27700 canonical form) and a data-file checker (`check`) — are planned but not built. See `README.md` and `docs/history.md` for what was deliberately cut.

## Commands

Dependencies are managed with uv; `uv.lock` is committed and CI runs `uv sync --locked`, so run `uv lock` and commit the result after changing `pyproject.toml`.

```bash
uv sync                                  # install (creates .venv)
uv run pytest                            # all tests
uv run pytest tests/test_catalogue_rules.py::test_duplicate_ids_are_caught
uv run ruff check . && uv run ruff format --check .
uv run catcheck catalogue.yaml           # exit 1 on error, 2 if the file will not load
uv run catcheck catalogue.yaml --strict  # warnings become errors
uv run catcheck catalogue.yaml --json
uv run catcheck --rules                  # list rule ids, severities, one-line docs
```

CI (`.github/workflows/ci.yml`) runs lint, format check, pytest and `catcheck catalogue.yaml` across Python 3.11–3.14. Ruff targets py311 (`requires-python >= 3.11`), so do not use syntax newer than 3.11 in `src/` even though `.python-version` is 3.14.

## Architecture

The catalogue is data; the code is a small engine over it. Three modules under `src/groundwork/`:

- `findings.py` — `Finding`, `Severity`, `summarise`, `sort_key`. Shared output shape for *every* checker in the toolkit (present `catcheck` and the future `check`), so `--json` consumers see one format. Keep it checker-agnostic.
- `catalogue/model.py` — `load()` (YAML → `Catalogue` of `Entry`), the controlled vocabularies (`VOCABULARIES`, `GRAIN_VINTAGES`, `REQUIRED_FIELDS`). `Entry` is a thin wrapper over the raw dict (`e.get(...)`, attribute access, `refs()` for all outgoing references). Vocabularies live in code deliberately: an unrecognised `boundary_vintage` must fail, not pass through. A legitimate new value is a one-line edit here.
- `catalogue/rules.py` — every rule is a generator `Catalogue -> Iterator[Finding]` registered with `@rule(id, name, severity)` into `REGISTRY`; `run()` executes them all and sorts errors first. No dispatch table to update. Rule id prefixes: `C` structure, `V` vocabulary, `R` references/lineage, `S` semantics, `W` completeness (advisory).
- `catalogue/cli.py` — the `catcheck` entrypoint (`argparse`, no subcommands).

### Design bias, and it is enforced

Rules are **generous about incompleteness and strict about silent wrongness**. A thin entry with only the nine required fields must pass with warnings only (`test_a_thin_entry_still_passes_without_errors`). Errors are reserved for things a reader would not notice: dangling references, a grain contradicting its vintage, one-sided `supersedes`/`superseded_by`, `status: reviewed` alongside a caveat containing "NOT verified". When adding a rule, pick the severity on that basis.

### Adding a rule

Write the decorated function in `rules.py` **and** a test in `tests/test_catalogue_rules.py` that breaks a copy of `BASE` in exactly that way. `test_every_registered_rule_has_a_test` greps the test file for every rule id literally, so the id string must appear in the test.

## Catalogue conventions

- One entry per *release*, not per dataset (`imd-2019` and `imd-2025` are separate entries linked by `supersedes`/`superseded_by`). Different releases often sit on different boundary generations and are not comparable; the catalogue exists to make that obvious.
- `status: draft` means unchecked against the publisher; `reviewed` requires clearing any "NOT verified" caveats first.
- Sources that no longer exist but are referenced get a `historical: true` stub, which must have `superseded_by`.
- `not_comparable_with` entries carry a `reason`; the reverse direction is warned about, not required.
- Field-by-field rationale is in `docs/catalogue-schema.md`; boundary-vintage and cross-generation join rules are in `docs/vintages.md`.

## Data policy

No licensed or personal data in this repository, on any branch. The catalogue describes sources; it never contains them. `.gitignore` blocks common data formats — never `git add -f` a data file.
