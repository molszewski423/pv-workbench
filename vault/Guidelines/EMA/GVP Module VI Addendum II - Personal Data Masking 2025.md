---
title: EMA GVP Module VI Addendum II — Masking of Personal Data in ICSRs (2025)
tags: [EMA, GVP, Module-VI, ICSR, EudraVigilance, personal-data, GDPR, masking]
source: "EMA GVP Module VI Addendum II (August 2025) — Masking of Personal Data in Individual Case Safety Reports Submitted to EudraVigilance"
jurisdiction: EMA
---

# EMA GVP Module VI Addendum II — Masking of Personal Data in ICSRs (2025)

## Background and Purpose

The EMA adopted **Addendum II to GVP Module VI** on **12 August 2025**, addressing the masking of personal data in Individual Case Safety Reports (ICSRs) submitted to EudraVigilance. This addendum was driven by GDPR compliance requirements and follows EU Implementing Regulation (EU) 2025/1466 (see separate note).

## Scope

Applies to all marketing authorisation holders (MAHs) and national competent authorities (NCAs) submitting ICSRs to EudraVigilance via the ICH E2B(R3) format.

## Key Requirements

### Personal Data Fields Subject to Masking

The following data elements must be masked (replaced with null or coded value) before ICSR submission to EudraVigilance when they contain directly identifiable personal data:

| E2B(R3) Field | Masking Requirement |
|---|---|
| Patient initials | Mask or use coded identifier |
| Date of birth (full) | Use year only or age range |
| Reporter name (non-HCP spontaneous) | Mask if consumer/patient reporter |
| Reporter address | Mask for non-healthcare professional reporters |
| Narrative free text | De-identify if patient name or DOB appears |

### Fields Exempt from Masking

- MedDRA coded terms (PTs, SOCs)
- Structured numeric/coded fields (age, weight, sex)
- Healthcare professional reporter identifiers (HCP name/institution retained)
- Regulatory-assigned case identifiers

## Implementation Timeline

- **12 August 2025**: Addendum II published and in effect
- MAHs must update their safety database export configurations to apply masking before EudraVigilance submission
- Existing submitted ICSRs: no retroactive masking required; applies to new submissions and follow-up reports

## Impact on Signal Detection

EMA confirmed that masking of personal identifiers does **not** affect:
- Disproportionality analysis (PRR, ROR)
- Case series and signal evaluation
- Causality assessment by regulators

Signal detection pipelines in EudraVigilance continue to operate on coded (MedDRA) data.

## MAH Obligations

1. Review safety database export settings to ensure personal data masking before E2B(R3) file generation
2. Update standard operating procedures (SOPs) for ICSR submission
3. Document masking rules in the pharmacovigilance system master file (PSMF)
4. Ensure masking does not remove data elements required for minimum valid ICSR (identifiable patient, suspect drug, adverse reaction, identifiable reporter)

## Relationship to GVP Module VI Rev 2

Addendum II supplements but does not replace GVP Module VI Rev 2 (2017). All other requirements of Module VI remain in effect, including:
- 15-day expedited reporting for serious unexpected ADRs
- 90-day periodic reporting for serious expected and non-serious ADRs
- Follow-up report obligations when new information becomes available
