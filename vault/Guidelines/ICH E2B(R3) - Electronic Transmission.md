---
title: ICH E2B(R3) — Electronic Transmission of Individual Case Safety Reports
tags: [ICH, E2B, E2B-R3, ICSR, electronic, XML, HL7, data-elements, regulatory]
source: "ICH E2B(R3) (2013) — Clinical Safety Data Management: Data Elements for Transmission of Individual Case Safety Reports"
jurisdiction: ICH
---

# ICH E2B(R3) — Electronic Transmission of Individual Case Safety Reports

## Purpose and Scope

ICH E2B(R3) defines the **data elements** required for electronic submission of Individual Case Safety Reports (ICSRs) to regulatory authorities. It replaces E2B(R2) and establishes a standardized global format for post-marketing and clinical trial safety reporting.

## Key Difference from E2B(R2)

| Feature | E2B(R2) | E2B(R3) |
|---|---|---|
| XML schema | Proprietary DTD | **HL7 ICSR v3** |
| Medical history | Free text | **Structured fields** |
| Lab data | Limited | **Expanded structured** |
| MedDRA version | Referenced | **Mandatory current version** |
| Narrative | Required | **Required + structured supplement** |
| Nullification | Manual | **Standardized nullification messages** |

## Core Data Elements (E2B(R3) Sections)

### C.1 — Identification of the Case Safety Report
- C.1.1: Sender's safety report unique ID
- C.1.2: Date of creation
- C.1.3: Type of report (spontaneous, study, literature, other)
- C.1.4: Date received by primary source
- C.1.5: Date received by sender
- C.1.6.1: Are additional documents available (Y/N)
- C.1.7: Does this case fulfill local criteria for expedited reporting?
- C.1.8: Worldwide unique case identification number
- C.1.9: Linked report(s) — for follow-up cases

### C.2 — Primary Source(s) of Information
- C.2.r.1: Reporter name and contact details
- C.2.r.2: Reporter's qualification (physician, pharmacist, consumer, etc.)
- C.2.r.3: Country where the reaction occurred
- C.2.r.4: Literature reference (if applicable)
- C.2.r.5: Is primary source from a regulatory authority?

### C.3 — Sender and Receiver
- Organization name, type, and contact details

### C.4 — Literature Reference
For literature-sourced cases: citation details

### C.5 — Study Identification
- Study name, study number, protocol number, study type
- Required for clinical trial ICSRs

### D — Patient Characteristics
- D.1: Patient initials
- D.2: Date of birth or age
- D.3: Age (onset of reaction)
- D.4: Age group (neonate, infant, child, adolescent, adult, elderly)
- D.5: Sex
- D.6: Weight (kg)
- D.7: Height (cm)
- D.8: Last menstrual period date (if applicable)
- D.9: Medical history (structured and coded with MedDRA)
- D.10: Relevant past drug history
- D.11: Parent information (if pediatric case)

### E — Reaction(s)/Event(s)
- E.i.1: Reaction description (verbatim term as reported)
- E.i.2: Reaction/event MedDRA LLT and PT
- E.i.3: Reaction outcome
- E.i.4: Start date of reaction
- E.i.5: End date of reaction
- E.i.6: Duration of reaction
- E.i.7: Seriousness criteria (death, life-threatening, hospitalization, disability, congenital anomaly, medically important)
- E.i.8: Was the reaction expected per applicable product information?

### F — Results of Tests and Procedures
- Structured data for laboratory tests, vital signs, biopsy results
- MedDRA-coded test names, numeric results, units, normal ranges

### G — Drug(s) Information
- G.k.1: Characterization of drug role (suspect, concomitant, interacting)
- G.k.2: Drug name and product details
- G.k.3: Authorization/registration number
- G.k.4: Dosage information
- G.k.5: Cumulative dose and unit
- G.k.6: Gestation period at time of drug exposure
- G.k.7: Indication for use
- G.k.8: Action taken with drug (withdrawn, dose reduced, not changed)
- G.k.9: Drug-reaction matrix (causality per drug-reaction pair)
- G.k.10: Additional information on drug

### H — Narrative Case Summary
- H.1: Case narrative (free text, required)
- H.2: Reporter's comments
- H.3: Sender's diagnosis (MedDRA coded)
- H.4: Sender's comments
- H.5: Case summary and comment on reaction

## Narrative Requirements (H.1)

The case narrative must be a complete stand-alone summary sufficient for regulatory review. It must include:
1. Patient demographics and relevant medical history
2. Suspect drug exposure (dose, route, indication, dates)
3. Concomitant medications
4. Description of the adverse event and clinical course
5. Outcome and treatment
6. Causality assessment
7. De-challenge/re-challenge information if applicable

The narrative should be written in past tense, third person, clinical prose. Abbreviations should be spelled out on first use.

## Seriousness Data Elements (E.i.7)

Seriousness is captured as checkboxes (multiple may apply):
- `resultsindeath` — results in death
- `lifethreatening` — life-threatening
- `hospitalization` — causes or prolongs hospitalization
- `disabling` — persistent or significant disability
- `congenitalanomali` — congenital anomaly or birth defect
- `seriousnessother` — other medically important condition

## Expectedness (E.i.8)

- 1 = Yes (expected per applicable product information)
- 2 = No (unexpected — not consistent with SmPC/IB)
- 3 = Unknown

## Causality (G.k.9)

Reporter's causality per drug-reaction pair:
- 1 = Related
- 2 = Not related
- 3 = Unknown

See also: [[ICH E2A - Clinical Safety Data]], [[MedDRA Coding Conventions]]
