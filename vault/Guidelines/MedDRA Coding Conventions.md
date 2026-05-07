---
title: MedDRA Coding Conventions and Hierarchy
tags: [MedDRA, coding, LLT, PT, HLT, HLGT, SOC, adverse-event, pharmacovigilance]
source: "MedDRA MSSO — MedDRA Term Selection: Points to Consider; ICH M1 MedDRA Guideline"
jurisdiction: BOTH
---

# MedDRA Coding Conventions

## MedDRA Hierarchy (Lowest to Highest)

```
LLT (Lowest Level Term)
  ↓ maps to
PT (Preferred Term)          ← Regulatory coding level
  ↓ grouped into
HLT (High Level Term)
  ↓ grouped into
HLGT (High Level Group Term)
  ↓ belongs to
SOC (System Organ Class)     ← 27 SOCs in MedDRA
```

**Regulatory reporting uses the Preferred Term (PT) level.** LLTs capture verbatim terms as reported; PTs are the standardized coding unit.

## The 27 System Organ Classes (SOCs)

Key SOCs relevant to pharmacovigilance:
- Blood and lymphatic system disorders
- Cardiac disorders
- Congenital, familial and genetic disorders
- Ear and labyrinth disorders
- Eye disorders
- Gastrointestinal disorders
- General disorders and administration site conditions
- Hepatobiliary disorders
- Immune system disorders
- Infections and infestations
- Injury, poisoning and procedural complications
- Investigations
- Musculoskeletal and connective tissue disorders
- Neoplasms benign, malignant and unspecified
- Nervous system disorders
- Psychiatric disorders
- Renal and urinary disorders
- Reproductive system and breast disorders
- Respiratory, thoracic and mediastinal disorders
- Skin and subcutaneous tissue disorders
- Surgical and medical procedures
- Vascular disorders

## Coding Level — Preferred Term (PT)

Each adverse event should be coded to the single most appropriate PT. Key principles:
- **One PT per distinct clinical event** — do not combine events into one PT
- **Code the diagnosis, not the symptoms** when a diagnosis is established (e.g., "hepatitis" not "elevated liver enzymes + jaundice + nausea")
- **Code symptoms separately** when no diagnosis is made
- **Use the most specific PT available** — avoid generic PTs like "Adverse event" or "Disease aggravated" when more specific terms exist

## Common Coding Decisions

### "Drug didn't work" / "Drug ineffective"
- **PT**: Drug ineffective
- **SOC**: General disorders and administration site conditions
- Also consider: Therapeutic product effect incomplete (more specific for incomplete efficacy)

### "Difficulty breathing" / "Can't breathe"
- If diagnosis confirmed: **PT**: Dyspnoea (SOC: Respiratory)
- If acute severe: **PT**: Acute respiratory failure
- If allergic: **PT**: Bronchospasm or Anaphylaxis depending on full clinical picture

### "Heart racing" / "Fast heartbeat"
- **PT**: Tachycardia (SOC: Cardiac disorders)
- If palpitations only (subjective, no documented rate): **PT**: Palpitations

### "Pins and needles in feet"
- **PT**: Paraesthesia (SOC: Nervous system disorders)
- If distal only: also consider Peripheral neuropathy if ongoing/progressive

### "Elevated liver enzymes with jaundice"
- If diagnosis established: **PT**: Hepatitis (specify type if known)
- If ischaemic: **PT**: Ischaemic hepatitis
- If toxic: **PT**: Toxic hepatopathy
- If only lab abnormality without diagnosis: code individual PTs (Alanine aminotransferase increased + Jaundice)

### "Anaphylaxis" vs "Anaphylactic reaction"
- **Anaphylaxis** — full clinical syndrome with confirmed diagnostic criteria (cardiovascular collapse, skin involvement, rapid onset)
- **Anaphylactic reaction** — reporter describes a hypersensitivity reaction without confirmed full anaphylaxis criteria
- Code what the reporter reports; do not upgrade or downgrade without clinical justification

### "Infection" — Coding Principles
- Code the specific pathogen and site when known: "Pneumonia pseudomonal" rather than "Pneumonia"
- Use infection PTs (SOC: Infections and infestations) not investigation PTs for confirmed infections
- "Blood culture positive" is an investigation PT — code alongside the infection diagnosis

## Multiplicity and Primary SOC

Each PT belongs to a **primary SOC** but may also be linked to **secondary SOCs** (multaxial). For regulatory reporting, the primary SOC is used. When selecting a PT, verify the expected primary SOC is clinically appropriate.

## Coding Flags for Senior Review

Mandatory senior reviewer sign-off required when:
- PT involves death, disability, or congenital anomaly (serious criteria)
- Multiple candidate PTs are clinically plausible and the choice affects seriousness classification
- Verbatim term describes a new or unlisted reaction not easily mapped to existing PTs
- Reporter's verbatim term is ambiguous between two distinct clinical entities
- Coding will be included in an expedited report or PSUR

## MedDRA Version

Always code to the **current MedDRA version** at the time of report processing. Version updates may retire, split, or modify PTs. Verify that selected PTs are active in the current version before submission.

## Common Errors to Avoid

- Coding a lab value as the adverse event when a clinical diagnosis is documented
- Using "Other" or "Not otherwise specified" PTs when specific terms exist
- Collapsing multiple distinct events into a single PT
- Selecting the SOC rather than a specific HLT/PT
- Using a retired or obsolete PT from a previous MedDRA version

See also: [[ICH E2B(R3) - Electronic Transmission]], [[ICH E2A - Clinical Safety Data]]
