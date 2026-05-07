---
title: FDA MedWatch and FAERS — Post-Marketing Safety Reporting
tags: [FDA, MedWatch, FAERS, post-marketing, spontaneous-reporting, NDA, BLA, 15-day, periodic, regulatory, US]
source: FDA MedWatch Safety Reporting Program; 21 CFR Part 314 Subpart B; FDA FAERS Technical Conformance Guide
jurisdiction: FDA
---

# FDA MedWatch and FAERS — Post-Marketing Safety Reporting

## MedWatch Program

MedWatch is the FDA Safety Information and Adverse Event Reporting Program for post-marketing surveillance of drugs, biologics, devices, and dietary supplements.

**Two reporting pathways:**
1. **Voluntary reporting** (MedWatch 3500): Healthcare professionals and patients report suspected ADRs directly to FDA — not required, but encouraged
2. **Mandatory reporting** (MedWatch 3500A): Industry mandatory reporting for NDA/BLA holders, device manufacturers

## FAERS — FDA Adverse Event Reporting System

FAERS is the FDA's pharmacovigilance database receiving post-marketing adverse event reports. It is the largest spontaneous reporting database in the world.

**Database scope**: All post-marketing ADR reports for drugs and biologics approved in the US.
**Access**: Public FAERS data available quarterly at openFDA API (`api.fda.gov/drug/event.json`).
**Data volume**: ~20+ million adverse event reports (growing ~2M/year).

### FAERS Data Structure
Each FAERS report contains:
- **Patient demographics**: Age, sex, weight
- **Drug information**: MedicinalProduct name, role (suspect/concomitant/interacting), dose, route, indication
- **Reaction**: MedDRA PT-coded adverse reactions (`reactionmeddrapt`)
- **Outcome**: Death, life-threatening, hospitalization, disability, other
- **Reporter**: Type (HCP, patient, attorney, other), country
- **Safety report metadata**: safetyreportid (unique), receivedate, transmissiondate

### FAERS Data Quality Issues

**Known artifacts requiring exclusion from signal analysis**:
- `"no adverse event"` — submitted for completeness or with documentation purposes
- `"off label use"` — administrative code, not an ADR
- `"drug ineffective"` — lack of efficacy, not a safety signal
- `"product quality issue"` — manufacturing/supply issue
- `"intentional product use issue"` — misuse/abuse coding
- `"drug use for unknown indication"` — administrative

**Structural biases**:
- **Reporting bias**: Recent, serious, or heavily publicized reactions are over-reported
- **Weber effect**: Sharp spike in ADR reports in year 2–3 post-approval, declining thereafter
- **Notoriety bias**: Media coverage increases reporting for specific drugs temporarily
- **Channeling bias**: Sicker patients receive newer drugs; signals in last-resort drugs may reflect patient severity
- **Missing denominator**: FAERS lacks total exposure data (numerator only)
- **Duplicate reports**: Same case from multiple reporters; deduplication by safetyreportid essential

## Mandatory Post-Marketing Reporting (21 CFR §314.81)

### 15-Day Alert Reports (ICSRs)
**Trigger**: Serious unexpected adverse drug experience from any source worldwide.
**Timeline**: 15 calendar days from first receipt.
**Submission**: Electronic via FDA ESG in E2B(R3) format.
**Applicability**: All NDA/BLA holders for approved drugs.

### 7-Day Alert Reports
**Trigger**: Fatal or life-threatening serious unexpected ADR.
**Timeline**: Initial report within 7 calendar days; complete report within 15 days.

### Periodic Adverse Drug Experience Reports (PADERs)
For the first 3 years post-approval: **quarterly** PADERs.
After 3 years: **annual** PADERs.
Content: Summary of all ADRs received during reporting period, line listing, signal analysis.

### 15-Day Aggregate Reports
FDA may request aggregate safety reports for specific signals on an ad hoc basis.

## openFDA FAERS API

**Base URL**: `https://api.fda.gov/drug/event.json`
**Authentication**: No API key required (rate limited); API key available for higher limits.
**Query syntax**: Lucene-based search (`patient.drug.medicinalproduct:cefiderocol`)
**Date filtering**: `receivedate:[20200101 TO 20241231]` (YYYYMMDD format)
**Pagination**: max 100 results per call; skip parameter max ~5000 (hard cap)
**Quarterly partitioning**: Required to get >5000 results for high-volume drugs

### Key FAERS API Fields
```
patient.drug.medicinalproduct   → drug name (primary search field)
patient.reaction.reactionmeddrapt → MedDRA PT of the adverse reaction
patient.drug.drugindication      → indication for use
safetyreportid                   → unique report ID (use for deduplication)
receivedate                      → date FDA received the report (YYYYMMDD)
patient.patientonsetage           → patient age
serious                          → 1=serious, 2=non-serious
seriousnessdeath                 → 1=fatal
```

## Disproportionality Analysis on FAERS

PRR (Proportional Reporting Ratio) and ROR (Reporting Odds Ratio) are the standard disproportionality statistics applied to FAERS:

**PRR** = `(a / (a+c)) / (b / (b+d))`
**ROR** = `(a/c) / (b/d)`

Where: a=drug+reaction, b=background+reaction, c=drug+no-reaction, d=background+no-reaction.

**Evans criteria** define a FAERS signal: PRR ≥ 2.0 AND N ≥ 3 AND χ² ≥ 4.0.

**FDA uses**: Multi-item Gamma Poisson Shrinker (MGPS, specifically EBGM) as primary signal detection tool internally, but PRR is standard for sponsor-initiated analyses.

## FAERS vs EudraVigilance Comparison

| Feature | FAERS | EudraVigilance |
|---|---|---|
| Regulator | FDA (US) | EMA (EU) |
| Public access | Full public via openFDA API | Limited public portal (line listings restricted) |
| Drug search | Free-text product name | EMEA number or active substance |
| Data scope | US-focused with global serious cases | EU cases + ICH partner reports |
| Signal detection | MGPS/EBGM (internal FDA) | EVDAS (EMA) with BCPNN |

## Relationship to Signal Management

FAERS data feeds into FDA signal management activities:
1. FDA CDER runs MGPS weekly on FAERS database
2. Signals meeting thresholds are evaluated by MedWatch team
3. Validated signals may trigger FDA communications (Drug Safety Communications, MedWatch alerts)
4. REMS programs may result from confirmed safety signals

For sponsors: quarterly FAERS mining using PBRER signal detection methodology required for periodic safety reporting.
