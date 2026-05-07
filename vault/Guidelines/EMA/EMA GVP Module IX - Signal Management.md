---
title: EMA GVP Module IX — Signal Management
tags: [EMA, GVP, GVP-IX, signal-management, PRAC, EudraVigilance, EVDAS, BCPNN, disproportionality, regulatory, EU]
source: "EMA/827661/2011 Rev 1 (2017) — Guideline on good pharmacovigilance practices (GVP) Module IX: Signal management"
jurisdiction: EMA
---

# EMA GVP Module IX — Signal Management

## Definitions

**Signal**: Information arising from one or multiple sources, including observations and experiments, which suggests a new potentially causal association, or a new aspect of a known association, between an intervention and an event or set of related events, either adverse or beneficial, that is judged to be of sufficient likelihood to justify verificatory action.

**Signal detection**: The process of identifying signals from available data sources.
**Signal validation**: Determining whether the signal constitutes a new aspect of the risk profile requiring further evaluation.
**Signal confirmation**: Formal evaluation and confirmation of validated signals.

## Data Sources for Signal Detection

### EudraVigilance (EV)
- The primary EU spontaneous reporting database for centrally authorised products
- MAHs have direct access to their own product data via EVWEB
- EMA monitors all EU ICSRs using EVDAS (EudraVigilance Data Analysis System)

### EVDAS — Signal Detection Methodology
**Primary statistic**: IC (Information Component) via Bayesian Confidence Propagation Neural Network (BCPNN)
- IC > 0 indicates disproportionate reporting
- IC025 (lower 95% CI) > 0 used as detection threshold for most applications
- Alternative: ROR (Reporting Odds Ratio) with Poisson assumption

**PRR also used**: For subgroup analyses, temporal trends, literature/registry data comparison.

### Additional Data Sources
- Literature monitoring (ongoing PubMed surveillance)
- Clinical trial data (periodic unblinded analyses, DSMB findings)
- Non-clinical studies (new toxicology data)
- Registries and observational studies
- PBRER/PSUR periodic data review
- Social media (emerging source, not yet regulatory standard)

## EU Signal Management Process

### Step 1: Signal Detection
- **EMA**: Automated weekly EVDAS runs on all ICSRs in EudraVigilance; pharmacovigilance specialists review outputs
- **MAHs**: Must monitor their product's safety database regularly; frequency proportionate to risk profile

### Step 2: Signal Validation
Assess whether the signal represents:
- A new association not previously documented
- A change in the frequency or severity of a known association  
- A new patient population or risk factor
- An unexpected interaction

**Outcome**: Validated (proceed to evaluation) or Not validated (document rationale, monitor).

### Step 3: Signal Prioritisation and Assessment
**Triage criteria**:
- Seriousness of the event
- Strength of evidence
- Clinical impact on benefit-risk balance
- Whether a risk minimisation measure could address the risk

**Prioritisation outcomes**:
- **Priority signal**: Immediate PRAC attention required
- **Non-priority signal**: Assessed at next routine PRAC review

### Step 4: Signal Evaluation
**By MAH**: Required to evaluate validated signals within specified timelines:
- Priority signals: rapid assessment (within 30 days typically)
- Non-priority signals: included in next PBRER or at routine signal review timepoint

**PRAC evaluation**: For signals with potential EU-wide impact or where MAH assessment is insufficient.
PRAC evaluation includes systematic literature review, epidemiological data, benefit-risk assessment.

### Step 5: Recommendation
PRAC may recommend:
- **Product information update**: SmPC/PIL amendment
- **RMP update**: New safety concern or risk minimisation measure
- **PASS**: Post-authorisation safety study to quantify risk
- **Referral**: Article 31/107 referral for pan-EU regulatory action
- **Suspension/revocation**: For serious safety concerns
- **No action**: Signal assessed as not representing a new safety concern

## MAH Signal Monitoring Obligations

Under EU regulations (Directive 2010/84/EU, GVP Module IX):
- MAHs must monitor their safety database for signals at defined intervals
- Signal monitoring frequency should be proportionate to safety concerns
- All validated signals must be evaluated and submitted to PRAC/NCAs if warranted
- Signals identified between PBRER cycles must be reported promptly

**Required reporting**: MAHs must submit signal assessments to EUDRACT/PRAC for designated medical events (DMEs) and priority signals on defined timelines.

## Designated Medical Events (DMEs)

The EMA maintains a list of DMEs — serious, often rare events where any case should trigger a signal assessment regardless of disproportionality statistics:
- Torsade de pointes / QT prolongation
- Drug-induced liver injury (DILI) with specified severity criteria
- Progressive multifocal leukoencephalopathy (PML)
- Aplastic anemia, agranulocytosis
- Angioedema
- Stevens-Johnson Syndrome / Toxic Epidermal Necrolysis
- Anaphylaxis

A single well-documented DME case may constitute a signal requiring assessment.

## Comparison with FDA Signal Management

| Aspect | EU (GVP Module IX / PRAC) | FDA (CDER/CBER Internal Process) |
|---|---|---|
| Primary database | EudraVigilance | FAERS |
| Detection method | BCPNN/IC (EVDAS) | MGPS/EBGM (internally) |
| MAH access to DB | EVWEB (own product data) | openFDA API (public) |
| Signal review body | PRAC | FDA drug safety staff |
| Public reporting | PRAC monthly meeting outcomes | Drug Safety Communications, FDA.gov |
| Response mechanism | SmPC update, PASS, referral | Label change, REMS, market withdrawal |

## Signal Management and PBRER Integration

Signals identified between PBRER cycles must either:
1. Be reported as interim safety updates to PRAC (if urgent)
2. Be evaluated within the next PBRER if non-priority

The PBRER includes a dedicated signals section summarizing all signals assessed during the reporting interval, with their validation status and regulatory outcome.
