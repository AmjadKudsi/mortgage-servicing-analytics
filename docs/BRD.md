# Business Requirements Document
## Mortgage Loan Performance Dashboard

---

### Stakeholder
VP of Mortgage Servicing Analytics, Home Lending Data & Analytics Team

### Purpose
Provide a recurring, interactive dashboard that enables servicing leadership to monitor portfolio health, identify emerging risk trends, and compare performance across loan vintages and geographies. The dashboard replaces manual report compilation with a self-service analytics tool.

### Refresh Frequency
Monthly (aligned with Freddie Mac LLD data release cycle)

---

### Business Questions

| # | Question | Priority | Why It Matters |
|---|----------|----------|----------------|
| 1 | What is the current delinquency rate across the portfolio, and how does it break down by DPD severity? | Critical | Drives staffing decisions for collections and loss mitigation teams. Reported to regulators. |
| 2 | Which states have the highest delinquency concentration, and how much UPB exposure sits in those states? | Critical | Identifies geographic concentration risk. Informs regional servicing strategies and disaster preparedness. |
| 3 | Which origination vintages are performing worst, and what borrower characteristics explain the differences? | High | Determines which segments of the book need proactive outreach. Informs credit risk appetite for future originations. |
| 4 | How are loans transitioning between delinquency states month over month? | High | Roll rates are the leading indicator of future losses. A rising 30→60 roll rate signals trouble before it shows in headline delinquency numbers. |
| 5 | Which borrower segments (credit score × LTV × vintage) carry the most risk relative to their portfolio share? | High | Enables targeted loss mitigation — focus resources on segments with the highest expected losses, not just the most loans. |
| 6 | How does loan behavior change as loans age (seasoning)? | Medium | Newer vintages may appear healthy simply because they haven't seasoned enough. The seasoning curve distinguishes real health from false comfort. |

---

### KPIs Required

| KPI | Definition | Target Display |
|-----|-----------|----------------|
| Total Loans | Count of active loans in portfolio | KPI card |
| Total UPB | Sum of current unpaid principal balance ($B) | KPI card |
| Delinquency Rate (30+ DPD) | Loans ≥30 DPD / Total loans × 100 | KPI card + trend |
| Serious Delinquency Rate (90+ DPD) | Loans ≥90 DPD / Total loans × 100 | KPI card |
| Average FICO | Mean credit score at origination | KPI card |
| DPD Distribution | Loan count per bucket: Current, 30, 60, 90, 120+ | Stacked bar |
| Roll Rates | Transition probability matrix between DPD states | Heatmap table |
| Delinquency by State | DLQ rate per state | Choropleth map |
| Delinquency by Vintage | DLQ rate per origination year | Bar chart |
| Risk Segment DLQ | DLQ rate by credit band × LTV bucket | Heatmap |

---

### Dashboard Pages

**Page 1 — Portfolio Health Overview** (answers questions 1, 2)
- KPI summary cards across the top
- Delinquency rate by vintage year (bar chart)
- Geographic delinquency heatmap (filled US map)
- DPD bucket distribution (horizontal bar)
- Global filters: vintage year, state, credit score band, property type

**Page 2 — Risk Migration & Segmentation** (answers questions 4, 5)
- Roll rate transition matrix (highlight table: from-state rows × to-state columns)
- Risk segment heatmap (credit score band × LTV bucket, colored by DLQ rate)
- Top 15 riskiest segments table (sorted by DLQ rate, showing loan count and UPB)
- Delinquency rate by credit score band (bar chart)

**Page 3 — Vintage & Behavioral Analysis** (answers questions 3, 6)
- Vintage comparison table (all metrics side-by-side, 11 years)
- Seasoning curve (line chart: DLQ rate by loan age, grouped by vintage era)
- Origination rate distribution by vintage (shows the rate environment each vintage entered)
- Credit score distribution by delinquency status

---

### Data Sources

| Source File | Refresh | Grain | Key Fields |
|------------|---------|-------|------------|
| `portfolio_summary.csv` | Monthly | Portfolio-level | Total loans, UPB, DLQ rate, avg FICO |
| `delinquency_by_dpd.csv` | Monthly | DPD bucket | Bucket, count, UPB, % of portfolio |
| `roll_rates.csv` | Monthly | From-bucket × to-bucket | Transition count and percentage |
| `risk_segments.csv` | Monthly | Segment | Credit band, LTV bucket, rate bucket, vintage, DLQ rate |
| `vintage_comparison.csv` | Monthly | Vintage year | 15 metrics per year |
| `geographic.csv` | Monthly | State | DLQ rate, loan count, UPB, avg FICO |
| `loans_detail.csv` | Monthly | Loan-level | 28 columns for ad-hoc analysis |

**Model Names:** The ML pipeline produces two models. The Origination Scoring Model ("OriginRisk") uses only features known at time of lending for genuine risk prediction. The Behavioral Segmentation Model ("SegmentIQ") uses all features including payment history for current portfolio risk ranking.

---

### Audience & Access
- Primary: Servicing leadership, risk management
- Secondary: Regulatory reporting team, portfolio strategy
- Access: Published to Tableau Public (public URL, read-only, interactive)

---

### Design Guidelines
- Color palette: Navy (#1a2332), white, gray, with red/amber/green for status indicators
- No chart junk — every visual element communicates data
- Title every chart with the business question it answers
- Tooltips on all data points showing exact values
- Consistent formatting across all 3 pages
