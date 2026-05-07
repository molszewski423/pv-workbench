---
tags: [vancomycin, AUC, MIC, nephrotoxicity, therapeutic-drug-monitoring, pharmacokinetics, MRSA, guideline-change]
source: "Rybak MJ et al. AJHSP 2020;77(11):835-864 (ASHP/IDSA/SIDP Consensus)"
jurisdiction: US
---

# Vancomycin AUC/MIC Consensus Guideline (2020)

## Overview and Regulatory Significance

In 2020, the American Society of Health-System Pharmacists (ASHP), Infectious Diseases Society of America (IDSA), and Society of Infectious Diseases Pharmacists (SIDP) published a revised consensus guideline replacing trough-based vancomycin monitoring with AUC/MIC-guided dosing for serious MRSA infections.

This guideline change has direct pharmacovigilance implications: it was motivated in part by accumulating FAERS and clinical trial evidence linking high-trough strategies to excess nephrotoxicity without commensurate efficacy benefit.

## Old Approach (Pre-2020): Trough-Guided Monitoring

- **Target**: Vancomycin trough serum concentrations of 15–20 mg/L for serious MRSA infections (pneumonia, bacteremia, endocarditis, osteomyelitis).
- **Rationale**: Trough surrogate for AUC exposure; assumed target attainment correlated with efficacy.
- **PV signal**: High trough targets associated with nephrotoxicity rates of 20–35% in critically ill patients. FAERS data from 2004–2019 captures this era of trough-driven dosing.
- **MedDRA PTs of concern**: Acute kidney injury, blood creatinine increased, renal failure, renal impairment, nephrotoxicity.

## New Approach (Post-2020): AUC/MIC-Guided Monitoring

- **Target**: AUC₂₄/MIC ratio of 400–600 mg·h/L (using population pharmacokinetic modeling or Bayesian estimation). MIC denominator assumes susceptible isolates (≤1 mg/L by BMD).
- **Rationale**: AUC/MIC better predicts both efficacy (bactericidal activity) and toxicity than trough alone. Avoids supratherapeutic troughs while maintaining efficacy.
- **Expected PV impact**: Reduction in FAERS nephrotoxicity reporting rates for patients managed with AUC-guided dosing (2020 onward), as lower troughs are acceptable when AUC targets are met.
- **Bayesian estimation**: Preferred method (e.g., software like JPKD, DoseMeRx, InsightRx) over nomogram-based approaches for AUC calculation.

## Pharmacovigilance Implications

### Signal Analysis Framework
The 2020 guideline change creates a natural before-after study design in FAERS:
- **Pre-2020 cohort** (2004–2019): Trough-driven dosing era — expect higher PRR for nephrotoxicity PTs.
- **Post-2020 cohort** (2020–present): AUC-guided era — expect attenuating nephrotoxicity signal if the guideline change is effective and widely adopted.

### Confounding Considerations
- Adoption lag: Not all institutions transitioned to AUC-guided monitoring immediately in 2020.
- Concomitant nephrotoxins (aminoglycosides, piperacillin-tazobactam, NSAIDs, IV contrast) are common confounders in FAERS.
- Population severity: Vancomycin is heavily used in ICU/septic patients with baseline renal compromise — confounding by indication is expected for AKI signals.
- Piperacillin-tazobactam combination: Pre-2020 data may reflect synergistic nephrotoxicity from Pip/Tazo combination therapy, an association that drove guideline reconsideration.

### Key MedDRA PTs for Nephrotoxicity Surveillance
| MedDRA PT | SOC | Relevance |
|---|---|---|
| Acute kidney injury | Renal and urinary disorders | Primary nephrotoxicity endpoint |
| Blood creatinine increased | Investigations | Sensitive AKI surrogate |
| Renal failure | Renal and urinary disorders | Severe endpoint |
| Renal impairment | Renal and urinary disorders | Milder dysfunction |
| Nephrotoxicity | Renal and urinary disorders | Direct toxicity labeling term |
| Blood urea increased | Investigations | BUN elevation marker |
| Oliguria | Renal and urinary disorders | Severe functional impairment |

## Regulatory Action Considerations

Under ICH E2E signal management principles:
- A **post-guideline reduction** in AKI PRR supports the efficacy of the 2020 guideline change and can be cited in PSUR safety updates for vancomycin products.
- A **persistent or increasing** AKI signal post-2020 would suggest inadequate adoption or continued risk in high-risk populations, potentially warranting label update or REMS consideration.
- Under EMA GVP Module VI, this type of temporal trend analysis supports characterization of risk-minimization measure effectiveness.

## Key References

- Rybak MJ, Le J, Lodise TP, et al. Therapeutic monitoring of vancomycin for serious methicillin-resistant Staphylococcus aureus infections: A revised consensus guideline and review by the American Society of Health-System Pharmacists, the Infectious Diseases Society of America, and the Society of Infectious Diseases Pharmacists. *Am J Health Syst Pharm.* 2020;77(11):835-864.
- Therapeutic Goods Administration (TGA) and [[EMA GVP Module VI - Signal Management]] — signal contextualization framework.
- [[ICH E2E - Pharmacovigilance Planning]] — signal evaluation and PSUR integration.
- [[Evans Criteria PRR Signal Detection]] — statistical thresholds for FAERS disproportionality.
