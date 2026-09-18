"""catcheck — check a source catalogue.

    catcheck catalogue.yaml            human-readable, exit 1 on error
    catcheck catalogue.yaml --strict   warnings count as errors
    catcheck catalogue.yaml --json     machine-readable
    catcheck --rules                   list the rules and what they do

This checks catalogue *entries* — metadata about sources. Checking a data
*file* against expectations is `check`, a separate command with its own rules
and the same finding format.
"""

from __future__ import annotations

import argparse
import json
import sys

from groundwork.findings import Severity, summarise

from groundwork.catalogue.model import CatalogueLoadError, load
from groundwork.catalogue.rules import REGISTRY, run


def cmd_rules() -> int:
    for r in REGISTRY.values():
        doc = (r.fn.__doc__ or "").strip().split("\n")[0]
        print(f"{r.id}  {r.severity.value:<7}  {r.name:<28}  {doc}")
    print(f"\n{len(REGISTRY)} rules.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="catcheck", description=__doc__)
    ap.add_argument("catalogue", nargs="?", help="path to catalogue.yaml")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--rules", action="store_true", help="list rules and exit")
    args = ap.parse_args(argv)

    if args.rules:
        return cmd_rules()
    if not args.catalogue:
        ap.error("a catalogue path is required")

    try:
        cat = load(args.catalogue)
    except CatalogueLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings = run(cat, strict=args.strict)
    counts = summarise(findings)

    if args.json:
        print(json.dumps({
            "checker": "catcheck",
            "input": str(cat.path),
            "entries": len(cat),
            "findings": [f.as_dict() for f in findings],
            "errors": counts[Severity.ERROR],
            "warnings": counts[Severity.WARNING],
        }, indent=2))
        return 1 if counts[Severity.ERROR] else 0

    for f in findings:
        print(f)

    historical = sum(1 for e in cat.entries if e.is_historical)
    drafts = sum(1 for e in cat.entries if e.get("status") == "draft")
    print(
        f"\n{len(cat)} entries ({len(cat) - historical} current, {historical} historical; "
        f"{drafts} still draft). "
        f"{counts[Severity.ERROR]} error(s), {counts[Severity.WARNING]} warning(s)."
    )
    return 1 if counts[Severity.ERROR] else 0


if __name__ == "__main__":
    sys.exit(main())
