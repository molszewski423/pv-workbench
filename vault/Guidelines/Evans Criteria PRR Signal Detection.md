---
title: Evans Criteria — PRR-Based Signal Detection
tags: [signal-detection, PRR, disproportionality, Evans, chi-squared, statistics, FAERS, pharmacovigilance]
source: Evans SJW, Waller PC, Davis S. Use of proportional reporting ratios (PRRs) for signal generation from spontaneous adverse drug reaction reports. Pharmacoepidemiol Drug Saf. 2001;10(6):483-6.
jurisdiction: BOTH
---

# Evans Criteria for PRR-Based Signal Detection

## The 2×2 Contingency Table

PRR analysis is based on a 2×2 table constructed from spontaneous adverse event reports:

|  | Drug of Interest | All Other Drugs |
|---|---|---|
| **Reaction of Interest** | a | b |
| **All Other Reactions** | c | d |

Where:
- **a** = cases with drug of interest AND reaction of interest
- **b** = cases with all other drugs AND reaction of interest
- **c** = cases with drug of interest AND all other reactions
- **d** = cases with all other drugs AND all other reactions

## Proportional Reporting Ratio Formula and Calculation

The Proportional Reporting Ratio (PRR) is calculated by dividing the proportion of the drug of interest's reports that mention the reaction by the proportion of all other drugs' reports that mention the same reaction:

```
PRR = (a / (a + c)) / (b / (b + d))
```

Step-by-step calculation:
1. **Numerator**: divide the drug-reaction cases (a) by all reports for the drug of interest (a + c) — this gives the reaction's reporting proportion for the drug
2. **Denominator**: divide background reaction cases (b) by all reports for all other drugs (b + d) — this gives the reaction's reporting proportion in the background
3. **Ratio**: divide numerator by denominator — values above 1.0 indicate over-reporting relative to background

A PRR of 2.0 means the reaction is reported twice as often proportionally for this drug compared to all other drugs in the database.

## Chi-Squared Statistic

```
χ² = Σ (O - E)² / E
```

Calculated as a standard chi-squared test on the 2×2 table. Observed values: [a, b, c, d]. Expected values derived from marginal totals assuming independence.

## Evans Signal Criteria (Classical Thresholds)

A **positive signal** requires ALL THREE conditions simultaneously:

| Criterion | Threshold | Rationale |
|---|---|---|
| PRR | **≥ 2.0** | Reaction ≥ 2× more frequent for this drug vs background |
| N (case count) | **≥ 3** | Minimum for clinical plausibility; excludes single-case noise |
| Chi-squared | **≥ 4.0** | Approximate statistical significance (p < 0.05 for 2×2 table) |

All three must be met simultaneously. A high PRR with N=1 is not a signal.

## Interpretation of PRR Values

| PRR Value | Interpretation |
|---|---|
| < 1.0 | Reaction under-represented; may indicate protective effect or coding artifact |
| = 1.0 | Reaction reported at same rate as background — no disproportionate signal |
| 1.0 – 2.0 | Mild elevation; below signal threshold; monitor |
| 2.0 – 5.0 | Signal threshold met (if N ≥ 3 and χ² ≥ 4); moderate elevation |
| 5.0 – 10.0 | Strong signal — warrants urgent signal validation |
| > 10.0 | Very strong signal — but may also reflect confounding or indication bias |

## Confounding by Indication

High PRR for mortality-related or severity-related outcomes in **last-resort therapies** (e.g., cefiderocol, colistin, daptomycin for resistant infections) is expected and does **not** constitute a de novo safety signal:

- These patients are inherently sicker than comparator populations
- Death, ICU admission, treatment failure are expected outcomes given severity of underlying infection
- PRR for death in cefiderocol vs meropenem reflects patient selection, not drug toxicity
- Always assess PRR in the clinical context of the indication

## Other Important Biases and Limitations

### Weber Effect (Reporting Lifecycle Bias)
Adverse event reporting rates are typically highest in the first 1–2 years after market authorization as prescribers are sensitized to new drug reactions. PRR values may decrease over time as the drug becomes more established, even if the underlying risk is unchanged.

### Masking Effect (Competition Bias)
A very strong signal for one drug-reaction pair can mathematically suppress detection of weaker signals for the same reaction in other drugs, because the background reaction count (b) is elevated. Can cause false negatives for masked signals.

### Notoriety Bias
High-profile safety signals (e.g., after a DHPC or black box warning) cause over-reporting of a specific reaction, inflating PRR for that drug-reaction pair.

### Underreporting Bias
The fundamental limitation of all spontaneous reporting systems. Estimated reporting rates for serious ADRs: 1–10% for most reactions. PRR identifies relative disproportionality, not absolute incidence.

### Reference Population Selection
PRR values are sensitive to the choice of background comparator drug or population:
- Narrow comparator (single drug, same class): controls for indication bias but may share class effects
- Broad comparator (entire database): maximizes N but includes diverse indications

## Comparison with Other Disproportionality Methods

| Method | Formula | Used By |
|---|---|---|
| PRR | (a/(a+c)) / (b/(b+d)) | MHRA, EMA, industry |
| ROR | (a×d) / (b×c) | EMA EudraVigilance |
| IC (BCPNN) | log₂(observed/expected) | WHO VigiBase |
| EBGM (GPS) | Empirical Bayes shrinkage | FDA FAERS |

PRR and ROR converge for rare reactions (small a relative to c, b relative to d). ROR tends to be larger for common reactions.

## Reporting Thresholds in Practice

EMA PRAC uses PRR ≥ 2 with N ≥ 3 as a minimum screening threshold for EudraVigilance signal detection, consistent with Evans criteria. FDA uses EBGM ≥ 2 from the GPS algorithm. Both approaches produce broadly comparable signal lists for well-populated databases.

## Reference

Evans SJW, Waller PC, Davis S. "Use of proportional reporting ratios (PRRs) for signal generation from spontaneous adverse drug reaction reports." *Pharmacoepidemiol Drug Saf.* 2001;10(6):483-6. doi:10.1002/pds.677

See also: [[EMA GVP Module VI - Signal Management]], [[ICH E2E - Pharmacovigilance Planning]]
