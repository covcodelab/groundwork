# Vintages

**Rules for choosing the right release of each source, and joining across them without silently invalidating the result.**

This is the knowledge behind most of the `caveats` in `catalogue.yaml`, and behind the checker's grain/vintage rules. If an entry says two sources are not comparable, the reason is usually here.

---

## Why this note exists

Every dataset in this project carries two dates that are routinely confused: the **boundary vintage** (which geography its codes belong to) and the **indicator reference period** (when the thing it measures was actually captured). Joining on an LSOA code that matches as a string, but belongs to a different boundary generation, produces a result that looks correct, passes every obvious check, and is wrong.

This is the most likely way this project produces a confidently incorrect risk map. It is worth an explicit specification.

---

## 1. The facts as they currently stand

**Indices of Deprivation**

| Release | Boundary vintage | Note |
|---|---|---|
| IMD 2010 | LSOA 2001 | |
| IMD 2015 | LSOA 2011 | |
| IMD 2019 | LSOA 2011 | Comparable with 2010 and 2015 |
| **IoD 2025** | **LSOA 2021** | **Not directly comparable with earlier indices** |

IoD 2025 is the current release and it changed more than the boundaries. It introduces 20 new indicators, substantially modifies 14 others, and replaces the shrinkage methodology (previously local-authority means, now based on area classification). The official position is that its outputs are "less directly comparable to previous indices."

**So an IMD series running 2019 → 2025 is not a time series.** If a model uses deprivation as a predictor over a pooled incident window, it must pick one release and hold it, and the choice should be the release whose reference period best covers the window. Mixing them to "keep deprivation current" across the window silently changes the predictor's definition partway through.

IoD 2025 also has **no single reference date**. Benefits data is March 2024, employment is the 2022/23 financial year, census-derived indicators are 2021. There is no one date to record, so the manifest needs the range and the note that it is heterogeneous.

**LSOA boundaries**

2021 LSOAs: 33,755 in England, 1,917 in Wales. They were created by splitting and merging 2011 LSOAs where population and household thresholds were breached — around **6% of LSOAs changed**. ONS publishes exact-fit and best-fit lookups between the two, carrying a change indicator per LSOA distinguishing unchanged, split, merged and irregular cases. Read the code values from the lookup itself rather than assuming them.

**Census 2021** is on LSOA 2021, so Census 2021 and IoD 2025 align natively. IMD 2019 and Census 2021 **do not**, and this is the specific join most likely to be made without thinking.

**Useful shortcut:** OHID publish earlier IMD releases adjusted onto later boundaries. Use those rather than building your own conversion — it is the published, citable version, and the provenance survives scrutiny in a way a bespoke conversion does not.

---

## 2. The principle that dissolves most of the problem

**Attribute at UPRN, at a point in time. Aggregate afterwards.**

Both candidate models work at UPRN level. So do not join area statistics to area statistics across vintages. Instead:

1. Take the UPRN as the atomic unit.
2. Attach area codes to it using a **vintage-stamped lookup** — UPRN → LSOA11, UPRN → LSOA21, UPRN → ward, UPRN → station ground, each recorded as a separate stamped column.
3. Attach each area-level covariate to the UPRN via the matching vintage column.
4. Aggregate to whatever geography the output needs, at the end.

The boundary-change problem then only arises where you genuinely need to compare *published area-level statistics* across vintages — a much smaller surface, and one where the change indicator lets you restrict to unchanged LSOAs.

The gazetteer is what makes this work. It is the join spine for the entire project, and its UPRN match rate is the ceiling on everything built above it.

---

## 3. Two tables, not one

This distinction is the other common silent error, and it is worth building into the schema.

**The modelling table — retrospective.** Covariates as they stood *at the time of each incident*. A fire in 2012 cannot be explained by 2024 deprivation; using current covariates to model historical events is anachronistic and, where the covariate has been influenced by the outcome, leaks. This table needs vintage-matched covariates per incident year, which is real work — and it is what makes a fitted model defensible.

**The targeting table — current.** Current covariates on current boundaries, used to decide who to visit now. Simpler, and it is what the operational user actually wants.

They answer different questions and they should be different tables with different names. The common failure is to build the targeting table and fit the model on it, which inflates apparent performance and makes the model a description of the present rather than a prediction.

Given the AUC figures already in play, be careful about how much of the reported discrimination survives doing this properly. That is a reason to check, not a reason to avoid checking.

---

## 4. Conversion rules, for when conversion is unavoidable

| Case | Rule |
|---|---|
| **Unchanged LSOA** | 1:1. Safe. |
| **Split** | Parent value may be inherited by children for a *rate* or *rank-derived band*. Never for a *count* — that duplicates. |
| **Merged** | Children combine with a proper denominator weight. Never a plain average. |
| **Irregular** | Flag and exclude from strict comparison. Do not fudge. |

**Never area-weight a rank.** IMD ranks and deciles are ordinal — interpolating them across boundary change is meaningless even though it is arithmetically possible. Convert underlying scores if you must convert anything, and prefer the published OHID adjustment to your own.

**Always carry the change indicator downstream** as a column on the output, so any comparison can be restricted to unchanged LSOAs when precision matters.

---

## 5. Vintages of the other sources

**Postcode lookups (ONSPD / NSPL)** are released quarterly and a postcode's LSOA assignment can change between releases. Stamp the release used. A postcode-mediated join is a second-best route anyway — prefer UPRN where you have it.

**Denominators.** Census 2021 household counts used as the denominator for incidents pooled 2010/11–2024/25 is an approximation that degrades the further you get from 2021, and degrades unevenly — new estates are the places where it is worst, and they are places you care about. Options, in order of preference: per-year dwelling counts from council tax records; mid-year estimates; or restrict the pooling window and accept smaller counts. Whichever is chosen, state it in the manifest, because it changes every rate on every map.

**Acorn** is periodically rebuilt; a household's Acorn type is not stable across builds. Record the build version. Note also that the Herts PH model derives its smoking variable from Acorn expenditure percentiles — so an Acorn rebuild silently changes a model predictor.

**EPC** is a lodgement register, not a survey. A dwelling's certificate is as-of its lodgement date, coverage is incomplete, and coverage is *biased* — recently sold and rented properties are over-represented. That bias correlates with tenure, which correlates with risk, so incomplete EPC coverage is not missing at random. Record the extract date and the coverage rate, and treat EPC-derived dwelling type as partially observed rather than known.

**Incident data** pooled 2010/11–2024/25 spans three LSOA generations and four IMD releases. Whatever window is chosen, record it and record which boundary generation the incidents were coded to at the time.

---

## 6. What to add to the manifest

Extending the model manifest from proposal v0.3:

```
boundary_vintage          -- lsoa11 | lsoa21 | uprn | none
indicator_reference_period -- range, plus a flag where heterogeneous
source_release            -- IoD2025, ONSPD 2026-05, Acorn build, EPC extract date
lookup_release            -- which UPRN/postcode lookup mediated the join
conversion_applied        -- none | ohid_adjusted | bespoke (+ method)
change_indicator_carried  -- bool
denominator_source        -- and its vintage
comparable_with[]         -- explicit allowlist of other model_ids
```

`comparable_with` is the honest counterpart to `predicts` from v0.3. Two models can predict the same quantity and still be incomparable because they sit on different boundary generations or different deprivation releases. Making that explicit and machine-readable means the interface can refuse the comparison rather than relying on the user to remember.

---

## 7. Validation rules that should fail the build

This is what turns the above from guidance into engineering. Each of these is a test in the pipeline, not a note in a wiki.

1. **Vintage match assertion.** Every join between an area code and an area statistic asserts that both carry the same `boundary_vintage`. Mismatch fails, rather than joining on a coincidentally-matching string.
2. **No silent conversion.** Any output combining sources of different vintages must carry a recorded `conversion_applied` value. Absent means fail.
3. **Gazetteer match rate.** Published as a metric, with a floor. A model scored over 94% of addresses has a 6% hole; that number belongs on screen, not in a footnote.
4. **Denominator coverage.** Every rate asserts a non-null, non-zero denominator for every unit, with the count of failures reported.
5. **Change indicator present** wherever an LSOA-level output crosses the 2011/2021 boundary.
6. **Referential integrity** from every UPRN in every model output back to the canonical gazetteer.
7. **Coverage by tenure/type for EPC-derived fields**, so the non-random missingness is visible rather than assumed away.

Rules 1 and 2 are the ones that would have caught the IMD 2019 / Census 2021 join.

---

## 8. Open decisions

1. **Which IMD release?** IoD 2025 aligns natively with Census 2021 and LSOA21 and is current — but is not comparable with what the Herts PH model may have used. Worth asking Public Health directly which release their model used, since that determines whether you can reproduce it.
2. **What pooling window for incidents?** The 15-year window gives counts but spans three boundary generations and four IMD releases. A shorter window aligned to one LSOA generation is cleaner and noisier. This is a genuine trade-off, not a right answer.
3. **Retrospective modelling table — build it or not?** It is materially more work. Skipping it means accepting that the model describes the present rather than predicting, which may be acceptable for targeting. Decide deliberately rather than by omission.
4. **Denominator source** — council tax dwelling counts per year, or Census 2021 held constant. Affects every rate.

---

## Sources

- [English indices of deprivation 2025: technical report](https://assets.publishing.service.gov.uk/media/68ff59c80f801e57b5bef907/ID_2025_Technical_Report.pdf)
- [OHID public health technical guidance — using the English indices of deprivation](https://fingertips.phe.org.uk/static-reports/public-health-technical-guidance/IMD/Using_IMD.html)
- [ONS Census 2021 geographies](https://www.ons.gov.uk/methodology/geography/ukgeographies/censusgeographies/census2021geographies) · [ONS statistical geographies](https://www.ons.gov.uk/methodology/geography/ukgeographies/statisticalgeographies)
- [LSOA (2011) to LSOA (2021) to LAD (2022) exact fit lookup for EW (V3)](https://www.data.gov.uk/dataset/03a52a27-36e7-4f33-a632-83282faea36f/lsoa-2011-to-lsoa-2021-to-local-authority-district-2022-exact-fit-lookup-for-ew-v3)
- [Hertfordshire household fire risk model (2026)](https://www.hertshealthevidence.org/documents/epi-content/report-household-fire-risk-model-public-2026.html)
