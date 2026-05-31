---
title: ICH E2B(R3) FDA Mandatory Compliance — April 2026 Deadline
tags: [ICH, E2B, E2B-R3, ICSR, FDA, IND, electronic-submission, HL7, mandate]
source: "FDA Final Guidance: Providing Regulatory Submissions in Electronic Format — IND Safety Reports (April 2024); mandatory compliance April 1, 2026"
jurisdiction: FDA
---

# ICH E2B(R3) FDA Mandatory Compliance — April 2026

## Background

The FDA published final guidance in **April 2024** requiring sponsors to submit IND safety reports in **ICH E2B(R3)** format. The mandatory compliance deadline is **April 1, 2026**.

This update replaces the prior E2B(R2) (MedDRA XML) format for IND safety submissions to FDA, aligning US requirements with the global ICH E2B(R3) standard already mandatory in EU (EudraVigilance) and Japan (PMDA).

## What Changes

### E2B(R2) → E2B(R3): Key Differences

| Feature | E2B(R2) | E2B(R3) |
|---|---|---|
| XML schema | Proprietary ICH DTD | **HL7 ICSR v3** |
| Data model | Case-level | **Event-level** (multiple events per case) |
| Medical history | Free text | **Structured coded fields** |
| Lab data | Limited | **Expanded structured** |
| Age categories | Numeric only | New categories (neonate, infant, etc.) |
| Nullification | Via follow-up | Dedicated nullification message type |
| Acknowledgement | Manual | Automated HL7 ACK messages |

### Submission Scope

Mandatory E2B(R3) applies to:
- **Postmarketing safety reports** (IND annual safety reports): effective January 2024 (voluntary phase)
- **Premarketing IND safety reports** (15-day and 7-day expedited reports): **mandatory April 1, 2026**
- 7-day fatal/life-threatening unexpected SUSARs
- 15-day other unexpected SUSARs

Not in scope:
- NDA/BLA postmarketing safety reports (separate rulemaking)
- Medical device adverse event reports (MedWatch 3500A)

## FDA-Specific Implementation Requirements

### Gateway and Validation

- Submit via **FDA ESG (Electronic Submissions Gateway)** using HL7 v3 ICSR transport
- Validate against FDA's published E2B(R3) validator before submission
- FDA provides test environment for pre-production validation
- Automated acknowledgements returned for accepted and rejected submissions

### FDA Appendix I(B) Data Elements

FDA requires additional data elements beyond the base ICH E2B(R3) standard (Appendix I(B)):
- NDC (National Drug Code) for US-marketed products
- FDA application number (NDA/BLA/IND)
- US-specific reporter type codes
- Case version number management per FDA conventions

### Transition Actions Required (Before April 1, 2026)

1. **Safety database upgrade**: Ensure system exports HL7 v3 ICSR XML (not legacy DTD)
2. **Mapping review**: Validate all E2B(R2) fields map correctly to E2B(R3) equivalents
3. **FDA validator testing**: Run test submissions through FDA's validation tool
4. **SOP updates**: Document new submission format, gateway procedures, ACK handling
5. **Training**: Safety operations and pharmacovigilance staff on new format and workflow
6. **Parallel testing**: Run E2B(R2) and E2B(R3) in parallel during transition period

## Signal Detection and Case Review Impact

E2B(R3) event-level structure enables:
- More granular causality assignment per individual event (vs. case-level in R2)
- Better data capture for multi-event cases (e.g., patient with 3 separate ADRs)
- Improved automated processing for FDA FAERS database ingestion
- Enhanced PRR/ROR calculations with better-structured case narratives

## Regulatory Reference

- FDA Final Guidance (April 2024): "Providing Regulatory Submissions in Electronic Format: IND Safety Reports"
- ICH E2B(R3) core guideline (2013, updated implementation guide)
- FDA Appendix I(B): FDA-specific data elements for E2B(R3) ICSRs
- Mandatory deadline: April 1, 2026 (24 months from guidance publication)
