# Where this came from

This repository replaces an earlier, much larger design. That design is archived at
[covcodelab/risk-model-explorer](https://github.com/covcodelab/risk-model-explorer) and is not being continued.
This note exists so nobody has to reconstruct the reasoning, and so the ideas that were cut are cut for a stated reason rather than forgotten.

## The earlier design

It began as a question about whether browser-local analytics — a SQL engine compiled to WebAssembly over static columnar files — could reduce reporting infrastructure cost. That reframed into spatial fire-risk modelling, and then grew, by individually reasonable steps, into:

- a national canonical data layer across four nations
- a model registry and transfer protocol, so a model built by one organisation could be run by another
- a three-tier local validation ladder
- combination rules for likelihood × consequence composites
- a GeoLibre plugin for comparing model outputs
- an open-source contribution strategy and a sector governance argument

Each step followed from the last. The sum was a multi-year programme, proposed by a team with flat headcount and two workstreams already live.

## Why it was cut

An adversarial review of the design surfaced problems that the incremental reasoning had hidden. The ones that landed:

**The design had inverted its own audience.** It promised to help services with marginal analytical capability reuse models built by better-resourced ones — then accumulated prerequisites (run the pipeline, obtain AddressBase, negotiate Acorn, produce a linked modelling table, pass a security review) that only well-resourced services could meet.

**A stale canonical layer is more dangerous than none**, because it keeps working. Automation handles the easy 90% of vintage maintenance; the hard 10% — IoD 2025 changing indicators, methodology and boundary generation at once — needs a human who understands deprivation indices, in year three, funded by nobody.

**Refusals get worked around.** An interface that declines to rank unvalidated models does not prevent the ranking; it relocates it to a spreadsheet where the caveats do not travel.

**The apparatus exceeded what it managed.** Registry, contract, comparison, validation ladder, shrinkage — sitting on models whose own authors report AUC around 0.59 and describe as "relatively poor at prediction".

**The time-saving claim was never measured.** It remains unmeasured. It is the premise of this repository too, and it is still the first thing that should be tested.

## What survived

The scope reset to the part that was never in doubt: **the burden of data discovery, acquisition and preparation**. Almost everything the review attacked was downstream of that; almost everything that survived the review is inside it.

Carried forward:

- the source catalogue, machine-readable, with the vintage and join knowledge that is the point
- the fetch / parse / conform separation
- content-addressed caching and read-only treatment of sources
- vintage-correctness rules and the checks that enforce them
- EPSG:27700 handling: analyse in 27700, display in 4326
- the principle that config declares the contract and code implements the procedure

Left behind: the model registry, the transfer protocol, the validation ladder, combination rules, the plugin, and the governance argument. If any of them become necessary, they can be built on this — they could not have been built without it.

## The one thing worth remembering

Scoping down converted a dangerous failure mode into an annoying one. A stale canonical layer serves confident maps that are quietly wrong. A stale catalogue entry means a 404 or a schema mismatch that an analyst hits immediately and fixes in a pull request.

That is most of the argument for this repository existing in the shape it does.
