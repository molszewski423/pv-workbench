---
title: 21 CFR Part 312 — IND Safety Reporting Requirements
tags: [FDA, IND, CIOMS, safety-reporting, SUSAR, expedited, 15-day, annual-report, regulatory, US]
source: 21 CFR Part 312 Subpart D — Responsibilities of Sponsors and Investigators (FDA)
jurisdiction: FDA
---

# 21 CFR Part 312 — IND Safety Reporting Requirements

## Overview

21 CFR Part 312 governs Investigational New Drug (IND) applications and establishes the sponsor's obligations for monitoring and reporting safety information during clinical development in the United States. Safety reporting requirements under §312.32 are the core mechanism for FDA oversight of drug safety during trials.

## Definitions (§312.32(a))

**Adverse event (AE)**: Any untoward medical occurrence associated with the use of a drug in humans, whether or not it is drug-related.

**Suspected adverse drug reaction (SADR)**: A reasonable possibility exists that the drug caused the event — causality cannot be ruled out.

**Serious adverse event (SAE)**: Results in death, is life-threatening, requires inpatient hospitalization or prolongation of existing hospitalization, results in persistent or significant incapacity or substantial disruption of the ability to conduct normal life functions, is a congenital anomaly/birth defect, or is an important medical event based on medical judgment.

**Unexpected adverse drug reaction (UADR)**: The nature or severity is not consistent with the applicable product information (e.g., Investigator's Brochure or FDA-approved labeling).

**Suspected Unexpected Serious Adverse Reaction (SUSAR)**: A SADR that is both serious AND unexpected.

## Expedited Reporting Requirements (§312.32(c))

### 7-Day IND Safety Reports
**Trigger**: Fatal or immediately life-threatening unexpected SUSAR.
**Submission**: Initial report within 7 calendar days of first awareness.
**Follow-up**: As complete a report as possible within 15 calendar days.

### 15-Day IND Safety Reports
**Trigger**:
- Serious AND unexpected SUSAR (not fatal/life-threatening)
- Any finding from clinical, epidemiological, pooled analysis, or animal study suggesting significant risk in humans (new finding of unexpected serious risk)

**Submission**: Within 15 calendar days of sponsor first receiving information.
**Content**: Narrative case summary, patient demographics, drug exposure, event description, causality assessment, follow-up plan.
**Format**: MedWatch 3500A or electronic equivalent via FDA Gateway; IND number required.

### Electronic Submission
Sponsors must submit expedited IND safety reports electronically using the FDA Electronic Submissions Gateway (ESG) in E2B(R3) format unless exempt. E2B(R3) data elements required per FDA technical specifications (M1 mapping).

## Annual IND Safety Report (§312.33)

**Submission**: Within 60 days of annual anniversary of IND going into effect.
**Content**:
- Summary of worldwide experience with drug safety
- All serious ADRs whether or not causally related
- IND Safety Reports submitted during the year
- Summary of subjects enrolled, deaths, dropouts, and adverse events by system organ class
- Any significant new safety findings from nonclinical studies
- General investigational plan for next year

## Causality Assessment Standards

FDA uses a "reasonable possibility" standard: a SADR exists when there is reason to believe that the drug caused or contributed to the event, considering:
- Temporal relationship (onset after drug initiation, resolution on dechallenge)
- Biological plausibility
- Absence of a more likely alternative explanation
- Prior literature or pharmacological mechanism

FDA does NOT use the ICH Causality Assessment terms (Certain/Probable/Possible etc.) — "reasonable possibility" is binary in the IND context.

## Comparator Drug Reporting

If an adverse event occurs with a comparator (marketed drug), the sponsor must follow the applicable IND safety reporting regulations for the investigational product if it is also involved, and may need to notify the marketed drug's NDA/BLA holder separately.

## Electronic Submission via ESG

**Gateway**: FDA Electronic Submissions Gateway (ESG)
**Format**: HL7 ICSR v3 XML (E2B(R3) format)
**Test system**: ESG test environment available for validation before production submission

## Relationship to Post-Marketing Reporting

Post-approval, safety reporting transitions to NDA/BLA regulations (21 CFR Part 314 for drugs, 21 CFR Part 600 for biologics):
- Expedited post-marketing reports: 15-day for serious unexpected reports; 7-day for fatal/life-threatening
- Periodic safety reports: Annual Safety Reports → replaces IND Annual Safety Report

## Key Differences from EMA Requirements

| Aspect | FDA (21 CFR §312.32) | EMA (GVP Module VI) |
|---|---|---|
| Expedited fatal/LT | 7 days | 7 days |
| Expedited serious unexpected | 15 days | 15 days |
| Causality standard | "Reasonable possibility" (binary) | ICH categorical terms |
| Periodic reporting | Annual IND safety report | PSUR per GVP Module VII |
| Electronic format | E2B(R3) via ESG | E2B(R3) via EudraVigilance |
| Regulator | FDA | EMA / National competent authorities |
