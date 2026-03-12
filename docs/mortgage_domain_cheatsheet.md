# Mortgage Servicing Domain Knowledge Guide

## THE MORTGAGE LOAN LIFECYCLE

This is the foundational mental model. Everything in mortgage analytics maps back to these stages.

### Stage 1: ORIGINATION
The borrower applies for a mortgage. A loan officer or broker collects income docs, credit reports, and property information.

**Key data:** Application date, borrower income, employment, requested loan amount, property address.

### Stage 2: UNDERWRITING
The lender evaluates risk. Can this borrower repay? Is the property worth enough to secure the loan?

**Key decisions:** Approve, deny, or approve with conditions. Set the interest rate (risk-based pricing).

**Key metrics created:**
- **Credit Score:** FICO score at origination (300-850).
- **LTV (Loan-to-Value):** Loan amount ÷ appraised property value. Higher LTV = more risk.
- **DTI (Debt-to-Income):** Total monthly debt ÷ gross monthly income. Typically capped at 43-50%.
- **CLTV (Combined LTV):** Accounts for any secondary liens (home equity loans).

### Stage 3: CLOSING
The loan is funded. Documents are signed. The borrower owns the home, and the mortgage is recorded.

**Key data:** Note date, first payment date, loan term (typically 360 months = 30 years), original interest rate, original UPB (Unpaid Principal Balance).

### Stage 4: SERVICING 
Once the loan closes, it enters **servicing** — the ongoing management of the loan for the life of the mortgage (potentially 30 years). 

**What a servicer does every month:**
- **Collects payments** from borrowers (principal + interest + escrow)
- **Remits funds** to the loan owner/investor (the servicer may not own the loan)
- **Manages escrow accounts** — holds money for property taxes and insurance, pays them when due
- **Sends periodic statements** to borrowers showing payment breakdown
- **Monitors delinquency** — tracks who's late, how late, and whether it's getting worse
- **Handles loss mitigation** — when borrowers can't pay, offers alternatives to foreclosure (forbearance, modifications, repayment plans)
- **Reports to investors** — provides data to Fannie Mae, Freddie Mac, or private investors on portfolio health
- **Manages escrow shortages/surpluses** — adjusts monthly payment if tax or insurance costs change
- **Handles payoffs and curtailments** — processes early payments (prepayments)

### Stage 5: PAYOFF (Happy Path)
The borrower pays off the loan — either by making all 360 payments, or by refinancing, or by selling the property.

**Key metric:** Prepayment — any principal paid ahead of schedule. This is tracked via CPR/SMM (explained in KPIs).

### Stage 6: DEFAULT (Unhappy Path)
The borrower stops paying. The loan moves through escalating stages of delinquency:

```
Current → 30-Day DPD → 60-Day DPD → 90-Day DPD → 120+ DPD → Foreclosure → REO
    ↑                                                                            |
    └──────── Cure (borrower catches up) ← Loss Mitigation (modification, etc.) ─┘
```

---

## PART 3: KEY TERMS — The Vocabulary You MUST Know

### Payment & Account Terms

| Term | Definition | Why It Matters for Analytics |
|------|-----------|------------------------------|
| **UPB (Unpaid Principal Balance)** | The remaining principal owed on the loan. Decreases each month as the borrower pays. | Primary measure of portfolio exposure. Total UPB = portfolio size. |
| **Escrow** | A separate account held by the servicer that collects borrower funds for property taxes and homeowner's insurance. The servicer pays these bills on behalf of the borrower. | Escrow shortages/surpluses affect monthly payment amounts. Mismanaged escrow is a top consumer complaint. |
| **P&I (Principal & Interest)** | The portion of the monthly payment that goes toward the loan balance and interest. | The predictable, calculable part of the payment. Amortization schedules show how P&I splits change over time. |
| **Curtailment** | An extra payment toward principal beyond the scheduled amount. Reduces the loan balance faster. | Tracked as unscheduled principal. Contributes to prepayment metrics (CPR/SMM). |
| **Amortization** | The process of paying off a loan through regular payments over time. Each payment splits between interest and principal — early payments are mostly interest, later payments are mostly principal. | FRM (Fixed-Rate Mortgage) vs ARM (Adjustable-Rate Mortgage) have different amortization behaviors. |

### Delinquency & Default Terms

| Term | Definition | Analytics Context |
|------|-----------|-------------------|
| **DPD (Days Past Due)** | How many days a payment is overdue. Reported in buckets: 30, 60, 90, 120+. | The primary metric for delinquency reporting. |
| **Delinquency** | A loan is delinquent when a payment is missed. Technically delinquent after the grace period (usually 15 days), but reported at 30-day intervals. | Delinquency Rate = (# delinquent loans) / (total active loans). The single most watched KPI in mortgage servicing. |
| **Default** | Generally, when a loan is 90+ days delinquent or the borrower has been referred to foreclosure. The precise definition varies by investor. | Default triggers different servicing workflows and reporting requirements. |
| **Foreclosure** | The legal process by which the lender takes possession of the property when the borrower defaults. Can be judicial (court-supervised, 12-18+ months) or non-judicial (faster, 4-6 months). | Foreclosure timelines vary dramatically by state. |
| **REO (Real Estate Owned)** | Property that the lender has acquired through foreclosure. The lender must then sell the property to recover losses. | REO inventory, time-to-sale, and loss severity on REO sales are key metrics. |

### Loss Mitigation Terms

| Term | Definition | Analytics Context |
|------|-----------|-------------------|
| **Loss Mitigation** | Any alternative to foreclosure that reduces the lender's losses. The servicer must evaluate delinquent borrowers for these options before proceeding to foreclosure. | Loss mitigation outcomes (success rate, re-default rate) are critical KPIs. CFPB requires servicers to track and report these. |
| **Forbearance** | A temporary pause or reduction in mortgage payments, typically 3-12 months. The borrower still owes the money — it's deferred, not forgiven. Massively expanded during COVID-19. | Forbearance entry/exit rates, duration, and post-forbearance outcomes are key metrics. |
| **Loan Modification** | A permanent change to the loan terms — may include rate reduction, term extension, principal forbearance (deferral), or capitalization of arrearages. | Modification re-default rate is a closely watched KPI. How many modified loans become delinquent again within 12/24 months? |
| **Repayment Plan** | An agreement where the borrower pays extra each month to catch up on missed payments over a set period (typically 3-6 months). | Repayment plan success rate (% that complete the plan) is tracked. |
| **Short Sale** | The borrower sells the property for less than the loan balance, with the servicer/investor's approval. The remaining balance may be forgiven. | Loss severity on short sales is typically lower than foreclosure — this is why servicers prefer them. |
| **Deed-in-Lieu (DIL)** | The borrower voluntarily transfers ownership of the property to the lender to avoid foreclosure. | Similar to short sale in terms of loss severity, but faster and less expensive. |
| **Loss Severity** | The percentage of the loan balance lost when a loan defaults. Calculated as: (Default UPB − Net Recovery) / Default UPB × 100. | Average loss severity is a portfolio-level KPI. Typically ranges from 25-40% depending on market conditions. |

---

## MORTGAGE SERVICING KPIs 

These are the specific metrics that a Home Lending Data & Analytics team produces.

### 1. Delinquency Rate

**What it is:** The percentage of loans in the portfolio that are past due, broken down by DPD bucket.

**How it's calculated:**
```
Delinquency Rate (30+ DPD) = Loans ≥ 30 DPD / Total Active Loans × 100

Reported by bucket:
  30-Day Rate  = Loans exactly 30 DPD / Total Active Loans
  60-Day Rate  = Loans exactly 60 DPD / Total Active Loans
  90-Day Rate  = Loans exactly 90 DPD / Total Active Loans
  90+ Day Rate = Loans ≥ 90 DPD / Total Active Loans (the "seriously delinquent" rate)
```

**From the data (16DI01):**
```
Current:  98.4%  (16,353 loans)
30 DPD:    0.7%  (109 loans)
60 DPD:    0.2%  (39 loans)  
90 DPD:    0.1%  (18 loans)
120+ DPD:  0.1%+ (scattered across deeper buckets)

Total 30+ Delinquency Rate ≈ 1.6%
Total 90+ Serious Delinquency Rate ≈ 0.2%
```
This is a healthy portfolio. National average for 30+ DPD is typically 3-5%.

**How it's reported:** Monthly, by vintage (origination quarter), state, loan type, servicer, and channel. The Tableau dashboard shows trend lines and geographic heatmaps.

### 2. Roll Rates (Transition Probabilities)

**What it is:** The probability that a loan moves from one delinquency status to another in a given month. This is the most analytically sophisticated servicing metric.

**How it's calculated:**
```
Roll Rate Matrix (Month N → Month N+1):

              To: Current  30-DPD  60-DPD  90-DPD  120+DPD  Payoff
From:
Current            97.5%    2.0%     —       —       —       0.5%
30-DPD             60.0%   15.0%   20.0%     —       —       5.0%
60-DPD             10.0%    5.0%   15.0%   65.0%     —       5.0%
90-DPD              5.0%     —      5.0%   10.0%   75.0%     5.0%
120+ DPD            2.0%     —       —      3.0%   80.0%    15.0%

(These are illustrative — actual rates vary by portfolio)
```

**Key terminology:**
- **"Rolling forward"** = moving to a worse delinquency bucket (30→60, 60→90)
- **"Curing"** = returning to current from a delinquent state
- **"Self-curing"** = loan returns to current without loss mitigation intervention
- **Cure Rate** = % of delinquent loans that return to current in a given month

**From the data:** The 48-character payment history string (field 38 in DI files) contains exactly this information. Each character represents one month: '0' = current, '1' = 30DPD, '2' = 60DPD, etc. We can compute roll rates by analyzing transitions between consecutive characters.

### 3. Prepayment Speed (CPR / SMM)

**What it is:** How fast borrowers are paying off their loans ahead of schedule (through refinancing, home sales, or curtailments).

**Key formulas:**
```
SMM (Single Monthly Mortality):
  SMM = Unscheduled Principal / (Beginning Balance − Scheduled Principal)
  
  Where:
    Unscheduled Principal = all principal payments beyond the scheduled amount
    (includes full payoffs, partial prepayments, curtailments)

CPR (Conditional Prepayment Rate):
  CPR = 1 − (1 − SMM)^12
  
  This annualizes the monthly prepayment rate.
  Example: If SMM = 0.5%, then CPR = 1 − (1 − 0.005)^12 ≈ 5.84%

PSA (Public Securities Association Benchmark):
  The industry-standard benchmark. 100% PSA assumes:
  - CPR starts at 0.2% in month 1
  - Increases by 0.2% each month
  - Levels off at 6% CPR after month 30
  
  200% PSA = twice the standard speed (faster prepayment)
  50% PSA = half the standard speed (slower prepayment)
```

**From the data:** With origination rates averaging 3.86% in a presumably higher-rate environment, these loans have little rate incentive to refinance — expect low CPR. Your current UPB vs original amounts shows cumulative principal reduction over the life of each loan.

### 4. Loss Severity

**What it is:** The percentage of the loan balance lost when a defaulted loan is liquidated.

**How it's calculated:**
```
Loss Severity = Total Loss / Default UPB × 100

Where:
  Total Loss = Default UPB 
               − Net Sales Proceeds 
               − MI Recoveries 
               − Non-MI Recoveries 
               + Foreclosure Costs 
               + Property Maintenance Costs 
               + Delinquent Interest

Typical components:
  Default UPB:           $250,000  (what was owed)
  Net Sales Proceeds:   −$180,000  (what the property sold for, minus selling costs)
  MI Recoveries:        −$15,000   (mortgage insurance payout)
  Foreclosure Costs:    +$12,000   (legal fees, property maintenance)
  Delinquent Interest:  +$8,000    (interest accrued while delinquent)
  ───────────────────────────────
  Total Loss:            $75,000
  Loss Severity:         30.0%
```

**From the data:** The Freddie Mac LLD files include fields for actual loss, net sales proceeds, MI recoveries, and expenses — all the components needed to compute loss severity on liquidated loans.

**Industry benchmarks:** Loss severity typically ranges from 25-40%. REO liquidations tend to have higher severity (~35-45%) than short sales (~20-30%).

### 5. Cure Rate

**What it is:** The percentage of delinquent loans that return to current status in a given period.

```
Monthly Cure Rate = Loans that moved from DPD → Current this month / 
                    Total loans that were DPD at start of month × 100

Can be broken down by bucket:
  30-Day Cure Rate: typically 55-70% (most 30-day delinquencies self-cure)
  60-Day Cure Rate: typically 20-40%
  90-Day Cure Rate: typically 10-20%
  120+ Cure Rate:   typically 5-10% (usually requires loss mitigation)
```

### 6. Modification Re-Default Rate

**What it is:** The percentage of modified loans that become delinquent again after modification.

```
12-Month Re-Default Rate = Modified loans that reach 60+ DPD 
                           within 12 months of modification / 
                           Total loans modified × 100

Typically tracked at 6, 12, 18, and 24-month horizons.
Industry average: 20-35% at 12 months (varies widely by modification type)
```

---

### Vocabulary Cheat Sheet
- "DPD buckets" (not "delinquency categories")
- "roll rates" (not "transition probabilities")
- "seasoning curve" (how loan behavior changes as the loan ages)
- "vintage analysis" (comparing loans originated in different quarters)
- "loss mit" (short for loss mitigation )
- "the book" or "the portfolio" (referring to the serviced loan portfolio)
- "CPR" and "SMM" (prepayment metrics)
- "severity" (short for loss severity)
- "cure" as a verb ("the loan cured" = returned to current)
- "REO pipeline" (properties in the foreclosure-to-sale process)

---

## MAPPING CONCEPTS TO DATA (16DI01)

Here's how every concept above connects to the actual Freddie Mac data:

| Concept | Field(s) in DI File | Example Value | What to Do With It |
|---------|-------------------|---------------|-------------------|
| Credit Score at Origination | Field 23 | 760 | Risk segmentation, ML feature |
| Current Credit Score | Field 62 | 771 | Track credit migration over time |
| LTV | Field 24 | 90 | Risk bucketing (high LTV = higher risk) |
| DTI | Field 26 | 37 | Affordability indicator |
| Loan Purpose | Field 19 | P (Purchase) | Segment analysis |
| Property State | Field 6 | GA | Geographic delinquency heatmap |
| Origination Date | Field 9 | 201610 | Vintage analysis |
| Loan Age | Field 34 | 41 months | Seasoning curve analysis |
| Current Interest Rate | Field 39 | 4.125% | Prepayment incentive calculation |
| Original Loan Amount | Field 13 | $275,000 | Portfolio exposure |
| Current UPB | Field 42 | $257,874.93 | Current exposure, prepayment calc |
| Delinquency Status | Field 37 | 00 (Current) | Primary KPI — delinquency rate |
| Payment History String | Field 38 | 48 chars of 0/1/2... | Roll rate analysis, pattern detection |
| Servicer Name | Field 33 | WELLS FARGO | Servicer performance comparison |
| MI Percent | Field 27 | 25% | Risk transfer analysis |
| Zero Balance Code | (if populated) | 01, 03, 06, etc. | Disposition type (payoff, short sale, REO) |
| Actual Loss | Field 56 | dollar amount | Loss severity calculation |
| First Default Date | Field 44 | 202003 | Time-to-default analysis |

---

## QUICK-REFERENCE FORMULAS

```
DELINQUENCY RATE
  = Count(loans where DPD ≥ 30) / Count(all active loans) × 100

ROLL RATE (e.g., 30→60)
  = Count(loans at 30-DPD in Month N that are at 60-DPD in Month N+1) 
    / Count(all loans at 30-DPD in Month N) × 100

CURE RATE (e.g., from 30-DPD)
  = Count(loans at 30-DPD in Month N that are Current in Month N+1) 
    / Count(all loans at 30-DPD in Month N) × 100

SMM (Single Monthly Mortality)
  = (Beginning Balance − Scheduled Principal − Ending Balance) 
    / (Beginning Balance − Scheduled Principal)

CPR (Conditional Prepayment Rate)  
  = 1 − (1 − SMM)^12

LOSS SEVERITY
  = (Default UPB − Net Recovery + Costs) / Default UPB × 100

MODIFICATION RE-DEFAULT RATE (12-month)
  = Count(modified loans reaching 60+ DPD within 12 months) 
    / Count(all modified loans) × 100
```

---