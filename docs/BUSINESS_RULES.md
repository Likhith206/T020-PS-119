# TENDERLENS — Business Rules Specification (BR-01 to BR-12)

This document provides the definitive specification of all business rules implemented in **TENDERLENS**, mapping them directly to statutory Indian Public Procurement standards (General Financial Rules 2017, CVC Guidelines, Public Procurement Policy for MSEs Order 2012, and Public Procurement Preference to Make in India Order 2017).

---

## BR-01: Bidder Eligibility Verification
- **Stage**: `ELIGIBILITY` (Stage 02)
- **Turnover Criterion**: The bidder's average annual financial turnover over the previous three financial years must be at least **30%** of the estimated tender cost.
  - *Boundary Rule*: Exactly 30% of the estimated cost **PASSES**.
- **Past Experience Criterion**: Similar completed works within the preceding **7 years** from the tender bid opening date:
  - **Option 1**: 1 similar completed work costing not less than **80%** of estimated tender cost.
  - **Option 2**: 2 similar completed works costing not less than **50%** of estimated tender cost each.
  - **Option 3**: 3 similar completed works costing not less than **40%** of estimated tender cost each.
- **Blacklisting**: Any bidder blacklisted or debarred by any government department on or prior to the bid opening date is classified as **`NON_RESPONSIVE`**.
- **MSE Relaxation**: Where `mse_relax_enabled` is active in the tender, valid registered Micro and Small Enterprises (MSEs) are granted exemption from prior turnover and experience criteria.

---

## BR-02: Earnest Money Deposit (EMD) Validation
- **Stage**: `TIMELINE_AND_EMD` (Stage 01)
- **Standard Requirement**: Mandatory EMD equal to **2.00%** of estimated tender cost, capped at a maximum ceiling of **₹50 Lakhs (₹5,000,000.00)**.
- **Exemptions**:
  - Registered MSEs holding a valid Udyam Registration Certificate.
  - DPIIT-recognized Startups.
- **Bank Guarantee Validity**: If furnished as a Bank Guarantee (BG), the instrument must remain legally enforceable for at least **45 calendar days** beyond the tender bid validity horizon.
  - *Boundary Rule*: A Bank Guarantee valid for exactly 45 additional days **PASSES**.
- **Forfeiture Triggers**:
  - Unilateral withdrawal or modification of bid during bid validity.
  - Failure by awarded contractor to furnish required Performance Security within 21 days of LoA.

---

## BR-03: Technical Qualification & Cut-offs
- **Stage**: `TECHNICAL_EVALUATION` (Stage 03)
- **Scoring Scale**: Evaluator scores normalized between 0.00% and 100.00%.
- **Weighted Aggregation**: Criterion scores are multiplied by tender criteria weights (summing to 100.00%).
- **Dual Cut-off Thresholds**:
  - **Individual Criterion Minimum**: At least **60.00%** on each scored criterion.
  - **Overall Weighted Minimum**: At least **70.00%** consolidated technical score.
  - *Boundary Rule*: Exactly 60.00% on any criterion and exactly 70.00% overall **PASSES**.
- **Two-Envelope Logical Protection**: Any failure on individual or overall cut-offs immediately marks the bidder **`TECHNICALLY_DISQUALIFIED`**. The bidder's financial envelope remains locked (`financial_envelope_opened = False`) and unread.

---

## BR-04: Financial Normalization & Arithmetic Corrections
- **Stage**: `FINANCIAL_EVALUATION` (Stage 04)
- **Commercial Base Normalization**:
  - If GST is excluded in price schedule, standard GST (18.00% or scheduled item rate) is added.
  - If freight is excluded (ex-works), freight amount is added to establish an all-inclusive delivered price (FOR Destination).
- **Arithmetic Correction Priority**:
  - Rule: **Unit Rate governs over extended item totals**.
  - `Corrected Item Amount = Quantity × Quoted Unit Rate`.
  - The corrected total is binding upon the bidder. Refusal to accept arithmetic corrections results in disqualification and EMD forfeiture.
- **Precision**: Calculated strictly using `decimal.Decimal` (never floating-point).

---

## BR-05: Public Procurement Preferences
- **Stage**: `PROCUREMENT_PREFERENCES` (Stage 06)
- **MSE Purchase Preference**:
  - Eligible MSEs quoting within an L1 + **15.00%** price margin band are invited to match the L1 price.
  - *Boundary Rule*: An MSE bid exactly 15.00% above L1 qualifies.
  - Quantity Allocation: Up to **25.00%** of total tender quantity.
- **Make in India (Class-I Local Supplier)**:
  - Local content declaration of at least **50.00%**.
  - Quoted price within an L1 + **20.00%** price margin band.
  - Quantity Allocation: Up to **50.00%** of total tender quantity.
- **Precedence Hierarchy**:
  1. MSE preference applied first (25%).
  2. Local supplier preference applied next on remaining quantity.
  3. Reserved Items: 100% quantity allocated exclusively to eligible MSE.

---

## BR-06: Competitive Bid Ranking (LCS & QCBS)
- **Stage**: `RANKING` (Stage 07)
- **Least Cost Selection (LCS)**:
  - Bids ranked ascending by final normalized comparative price (L1, L2, L3...).
  - Tie-breakers: 1) Higher technical score, 2) Earlier submission timestamp.
- **Quality and Cost Based Selection (QCBS)**:
  - Configurable ratio (Default: 70% Technical, 30% Financial).
  - `Financial Score = (L1 Price / Bidder Price) × 100`.
  - `Composite Score = (Tech Score × Tech Weight %) + (Fin Score × Fin Weight %)`.
  - Highest composite score wins (H1).
  - Tie-breakers: 1) Lower financial price, 2) Higher technical score, 3) Earlier timestamp.

---

## BR-07: Abnormally Low Bid Analysis
- **Stage**: `ABNORMAL_BID_ANALYSIS` (Stage 05)
- **Trigger Conditions (Strict Inequality)**:
  1. Price strictly less than **85.00%** of estimated tender cost (`Price < 0.85 × Estimate`).
     - *Boundary Rule*: A price of exactly 85.00% of estimate does **NOT** trigger this condition.
  2. Price strictly less than **80.00%** of the average qualified bid price (`Price < 0.80 × Avg`).
- **Rate Justification Protocol**:
  - If capacity justification is missing or rejected -> Bid is rejected; evaluation proceeds to next bidder.
  - If accepted -> Imposes **5.00%** base performance security plus additional security equal to the shortfall percentage below 85% of estimated cost.

---

## BR-08: Bid Validity and Extensions
- **Stage**: `BID_VALIDITY` (Stage 08)
- **Standard Horizon**: **90 calendar days** from bid opening date.
  - *Boundary Rule*: Award action on Day 90 is valid.
- **Extension Protocol**: Procuring entity may request one **30-day** validity extension.
- **Non-Punitive Exit**: A bidder declining the validity extension exits the procurement process cleanly without forfeiture of EMD. Award issued after validity expiry without formal extension is void ab initio.

---

## BR-09: Contract Award & Performance Security
- **Stage**: `AWARD_AND_SECURITY` (Stage 09)
- **Letter of Acceptance (LoA)**: Issued to the winning bidder within bid validity.
- **Standard Performance Security**: **3.00%** of total contract value.
- **Abnormal-Low Performance Security**: **5.00%** plus additional security.
- **Submission Window**: Contractor must deposit security within **21 calendar days** of LoA.
- **Default & Fallback Rule**:
  - If security is not submitted within 21 days: EMD is forfeited and LoA cancelled.
  - Contract is offered to the next-ranked bidder (L2) at their quoted rate if within **10.00%** of L1 price. Otherwise, re-tender is triggered.

---

## BR-10: Single Responsive Bid & Competition Safeguards
- **Stage**: `RANKING` (Stage 07)
- Where only a single responsive bid is received:
  - If `single_bid_allowed` is enabled -> Evaluation and award may proceed with documented market justification.
  - If `single_bid_allowed` is disabled -> Re-tender is mandatory to ensure public accountability and price discovery.

---

## BR-11: Price Negotiation Protocol
- **Stage**: `AWARD_AND_SECURITY` (Stage 09)
- In compliance with Central Vigilance Commission (CVC) norms:
  - Post-tender negotiation is permitted **strictly with the L1 bidder**.
  - Triggered only if L1 price exceeds estimated cost by more than **10.00%**.
  - Negotiated price cannot exceed original L1 price and cannot result in re-ranking.

---

## BR-12: Pipeline Orchestration & Rule Precedence
- **Stage**: `ORCHESTRATION` (Core Architecture)
- Governs the strict sequential execution order:
  1. Timeline & EMD -> 2. Eligibility -> 3. Technical Evaluation -> 4. Financial Evaluation -> 5. Abnormal Bid Analysis -> 6. Procurement Preferences -> 7. Ranking -> 8. Bid Validity -> 9. Award & Security.
- **Cascading Blockage**: If a bidder fails any mandatory gate, all downstream stages are immediately marked `BLOCKED`, and subsequent evaluations (especially financial disclosure) are barred.
