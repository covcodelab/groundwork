# Contributing

The catalogue only works if adding an entry is a five-minute job. Everything below is shaped by that.

---

## Adding a source

Open `catalogue.yaml`, copy a nearby entry, change it, open a pull request. You do not need Python, and you do not need to understand the checker.

**The minimum that will pass:**

```yaml
  - id: my-source-2025
    title: The name the publisher uses
    publisher: Who is responsible for it
    country: england          # or wales | scotland | northern-ireland | ew | gb | uk
    url: https://example.gov.uk/the-landing-page
    licence: OGL-UK-3.0
    tier: open                # or licensed | internal | restricted
    grain: lsoa               # what one row represents
    boundary_vintage: lsoa21  # which generation of that geography
    status: draft
    entry_added: 2026-09-18
```

That is a useful entry. Add more when you know more.

**What to add next, in order of how much it helps someone:**

1. `caveats` — the things that cost you an afternoon. This is the field the catalogue exists for. Be specific and be blunt: "Joining this to Census 2021 on an LSOA code is silently wrong" beats "check compatibility".
2. `key` and `join_via` — the actual column name as published (`LSOA21CD`, not "LSOA code") and how you get from this to something else.
3. `not_comparable_with` — with a reason. More useful than listing what *is* comparable, because the failure is silent.
4. `keywords` and `description` — so search finds it.

## Rules that will stop you

Run the checker before opening the PR. CI runs it too.

```bash
uv run catcheck catalogue.yaml
```

Errors are things that cause silent wrongness:

- A reference to an entry that does not exist
- A grain that contradicts its boundary vintage (an LSOA source on a Scottish data zone vintage)
- `supersedes` declared on one side only
- `status: reviewed` while a caveat still says NOT verified
- A value outside the controlled vocabulary — usually a typo (`lsoa2021` for `lsoa21`). If your value is legitimate, add it to the vocabulary in `src/groundwork/catalogue/model.py` in the same PR.

Warnings are incompleteness. They will not block you. `--strict` turns them into errors if you want a higher bar for your own work.

## Two conventions worth knowing

**One entry per release, not per dataset.** `imd-2019` and `imd-2025` are separate entries. They are on different boundary generations and are not comparable, which is exactly the thing the catalogue exists to make obvious. Link them with `supersedes` / `superseded_by`.

**`status: draft` means nobody has checked it against the publisher.** That is the honest default for a new entry and there is no shame in it — a draft entry is far more useful than no entry. Change it to `reviewed` only when you have opened the source and confirmed the fields, and clear any "NOT verified" caveats when you do. The checker enforces that pairing.

## What does not belong here

**No data.** The catalogue describes sources; it never contains them. `.gitignore` blocks common data formats as a safety net — if you find yourself using `git add -f` on a data file, stop and reconsider.

**No licensed content.** Describing Acorn or AddressBase is fine and useful. Including anything derived from them is not.

**No column-level schemas.** Tempting, and it would double the maintenance burden while going stale faster than anything else. Column detail belongs to the parser, which fails loudly when it drifts.

## Changing the code

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Adding a rule means writing a decorated function in `src/groundwork/catalogue/rules.py` **and** a test that breaks the catalogue in that specific way. This is enforced — `test_every_registered_rule_has_a_test` fails if a rule id never appears in the test file. A checker nobody has watched fail is not a checker.

## Dependencies

Managed with [uv](https://docs.astral.sh/uv/). `uv.lock` is committed and CI runs `uv sync --locked`, so run `uv lock` and commit the result if you change dependencies.
