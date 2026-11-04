# TENDERLENS — 5-Minute Faculty Demonstration Script
## PS-119: Explainable & Intelligent Procurement Evaluation Engine
### Tagline: Every Bid Evaluated. Every Decision Explained.

---

## Demonstration Overview & Objective
This live demonstration walks through the end-to-end evaluation of **Tender TND001** (Enterprise Cloud Infrastructure, Estimated Cost: ₹5,00,00,000.00 / ₹5 Crore), showcasing all major differentiators:
1. **Rule Precedence Pipeline (BR-12)**
2. **Two-Envelope Financial Protection**
3. **Unit-Rate Arithmetic Corrections**
4. **Public Procurement Preferences (MSE 15%/25% & Make-in-India 20%/50%)**
5. **Procurement Decision Graph (DAG) with Cascading Blockage**
6. **Explainable Decision Trace**
7. **Tamper-Evident SHA-256 Audit Verification**
8. **Isolated What-If Contingency Simulation**
9. **Procurement Risk Intelligence**

Estimated Duration: **5 Minutes**.

---

## Step 1: Environment Initialization & Schema Creation (30 Seconds)

### Command:
```powershell
python main.py init-db --reset
```

### Expected Output:
```text
Database initialized successfully at database/tenderlens.db with schema.
```

### Faculty Explanation:
> *"We initialize our SQLite database with foreign keys enabled across all 21 normalized relational tables. Every monetary value is stored as high-precision text mapped to Python's `Decimal` class—guaranteeing zero floating-point approximation error across all tender calculations."*

---

## Step 2: Tender Publishing & Bid Ingestion (45 Seconds)

### Commands:
```powershell
python main.py create-tender --file data/input/tenders.csv
python main.py list-tenders
python main.py import-bids --tender TND001 --file data/input/bids.csv
python main.py list-bids TND001
```

### Expected Output:
```text
Created Tender: TND001 | Title: Modernization of Enterprise Cloud Infrastructure... | Est Cost: ₹5,00,00,000.00 | Mode: LCS
Created Tender: TND002 | Title: Smart City Integrated IoT Video Analytics... | Est Cost: ₹8,00,00,000.00 | Mode: QCBS

Registered Bid: BID_T1_001 for Bidder: Alpha Cloud Solutions Pvt Ltd (BDR001)
Registered Bid: BID_T1_002 for Bidder: Beta Infotech Enterprises (MSE) (BDR002)
...
Successfully imported bids and related documents for Tender: TND001
```

### Faculty Explanation:
> *"We import 8 diverse bidder personas into Tender TND001. Notice that all bids are initially marked with `technical_envelope_opened = False` and `financial_envelope_opened = False`. Financial price schedules remain logically and physically locked until technical qualification is certified."*

---

## Step 3: Master Evaluation Pipeline Execution (45 Seconds)

### Command:
```powershell
python main.py evaluate TND001
```

### Expected Output:
```text
Executing TENDERLENS Evaluation Pipeline for Tender: TND001...

======================================================================
EVALUATION COMPLETE | Status: AWARDED
Awarded Bidder:   BDR007
Contract Value:   ₹3,90,00,000.00
LoA Reference:    LOA/TND001/BDR007/2026
Security Due:     ₹46,80,000.00 (by 2026-11-25)
======================================================================
```

### Faculty Explanation:
> *"The engine executed all 9 stages in strict sequence under BR-12. Out of 8 bidders:
> - Bidder BDR005 was disqualified at Stage 1 due to insufficient Bank Guarantee validity (only 16 days beyond bid validity vs mandatory 45 days).
> - Bidder BDR004 was disqualified at Stage 2 due to insufficient turnover (< 30% of estimate).
> - Bidder BDR006 was disqualified at Stage 3 because its score on Methodology was 52% (failing the mandatory 60% individual cut-off).
> - The financial envelopes of BDR004, BDR005, and BDR006 remained strictly unopened!
> - Bidder BDR008 had an arithmetic error in its schedule (quoted total ₹4.70 Cr vs unit-rate sum ₹4.536 Cr), which was automatically corrected using unit-rate priority under BR-04."*

---

## Step 4: Consolidated Dossier & Comparative Statement (45 Seconds)

### Command:
```powershell
python main.py report TND001
```

### Expected Output:
```text
================================================================================
TENDERLENS — CONSOLIDATED PROCUREMENT EVALUATION REPORT
================================================================================
Tender ID:        TND001
Estimated Cost:   ₹5,00,00,000.00
Evaluation Mode:  LCS
Current Status:   AWARDED
--------------------------------------------------------------------------------
Rank  | Bidder ID  | Bidder Name              | Quoted Total     | Corrected Price  | Tech %  | Status      
--------------------------------------------------------------------------------------------------------------
L1    | BDR007     | Theta Computing Platfo.. | ₹3,90,00,000.00  | ₹3,90,00,000.00  | 72.10   | AWARDED     
L2    | BDR001     | Alpha Cloud Solutions .. | ₹4,40,00,000.00  | ₹4,40,00,000.00  | 84.35   | NONE        
L3    | BDR008     | Iota Solutions India     | ₹4,70,00,000.00  | ₹4,53,60,000.00 * | 80.50   | NONE        
L4    | BDR002     | Beta Infotech Enterpri.. | ₹4,85,00,000.00  | ₹4,85,00,000.00  | 75.95   | NONE        
L5    | BDR003     | Gamma Networks & Syste.. | ₹5,10,00,000.00  | ₹5,10,00,000.00  | 79.60   | NONE        
--------------------------------------------------------------------------------------------------------------
(*) Indicates arithmetic corrections were applied to match unit-rate calculations.
```

---

## Step 5: Procurement Decision Graph & Cascading Blockage (45 Seconds)

Show the Decision Graph for **BDR006** to demonstrate cascading blockage and Two-Envelope protection:

### Command:
```powershell
python main.py decision-graph TND001 --bidder BDR006
```

### Expected Output:
```text
=================================================================
TENDERLENS | PROCUREMENT DECISION GRAPH
Tender: TND001 | Bidder: BDR006
=================================================================

[PASS] 01. TIMELINE_AND_EMD
          ↓
[PASS] 02. ELIGIBILITY
          ↓
[FAIL] 03. TECHNICAL_EVALUATION
    Decision: Technical disqualification: One or more individual criteria scored below 60.00%...
          ↓
[BLOCK] 04. FINANCIAL_EVALUATION
    Decision: Upstream stage 'TECHNICAL_EVALUATION' failed or was blocked.
          ↓
[BLOCK] 05. ABNORMAL_BID_ANALYSIS
          ↓
[BLOCK] 06. PROCUREMENT_PREFERENCES
          ↓
[BLOCK] 07. RANKING
          ↓
[BLOCK] 08. BID_VALIDITY
          ↓
[BLOCK] 09. AWARD_AND_SECURITY

-----------------------------------------------------------------
FINAL DECISION STATUS: DISQUALIFIED / BLOCKED
=================================================================
```

### Faculty Explanation:
> *"This is our primary architectural differentiator: the Procurement Decision Graph. Notice how BDR006 passed Stages 1 and 2, but failed Stage 3 on the 60% methodology cut-off. Immediately, our cascading blockage algorithm blocked Stages 4 through 9. Node 04 Financial Evaluation was never unlocked. The graph is reconstructable directly from SQLite."*

---

## Step 6: Explainable Decision Trace (30 Seconds)

### Command:
```powershell
python main.py explain-stage TND001 BDR001 technical
```

### Expected Output:
```text
======================================================================
TENDERLENS | EXPLAINABLE DECISION TRACE
======================================================================
[RULE BR-03] STAGE: TECHNICAL_EVALUATION | RESULT: PASS
  Explanation: Technical qualification successful: Overall weighted score is 84.35%, meeting or exceeding 70.00% with all individual cut-offs cleared.
  Calculation: Total Weighted Score = 84.35% >= 70.00%: True, All individual >= 60.00%: True
  Input Snapshot: {'criterion_scores': {'CRIT_EXPERIENCE': '85.00', ...}, 'total_weighted_score': '84.35'}
  Required Thresholds: {'min_overall_score_pct': '70.00', 'min_individual_pct': '60.00'}
  Evidence: Consolidated Technical Scorecard
```

---

## Step 7: Cryptographic Tamper-Evident Audit Ledger (30 Seconds)

### Command:
```powershell
python main.py audit-verify TND001
```

### Expected Output:
```text
======================================================================
TENDERLENS | AUDIT CHAIN VERIFICATION — TENDER: TND001
======================================================================
Status: VERIFIED - 100% UNTAMPERED

Findings:
  * Audit chain completely verified. Total 15 events intact with valid SHA-256 links.
======================================================================
```

### Faculty Explanation:
> *"Every single state transition is hash-linked using SHA-256 with $H_n = \text{SHA256}(H_{n-1} + \text{Event}_n)$, anchored to a 64-zero genesis hash. If an attacker modifies or deletes a single database row, `audit-verify` immediately detects the tampering and identifies the exact sequence number."*

---

## Step 8: Isolated What-If Simulation Sandbox (30 Seconds)

### Command:
```powershell
python main.py simulate TND001 --scenario l1_withdrawal
```

### Expected Output:
```text
======================================================================
SIMULATION RUN: SIM_L1_WITHDRAWAL_...
Scenario: l1_withdrawal
----------------------------------------------------------------------
Original Outcome:
  {"winner": "BDR007", "contract_value": "39000000.00"}

Simulated Outcome & Structural Diff:
  * Original L1 bidder (BDR007) withdrew. EMD forfeited. New awarded contractor is BDR001.

Official tender and audit ledger remained 100% untouched.
======================================================================
```

### Faculty Explanation:
> *"We simulate contingency scenarios using an in-memory database clone. When L1 withdraws, BDR007's EMD is forfeited in the simulation and BDR001 is promoted to winner—while our official production records remain 100% intact."*

---

## Step 9: Automated Test Suite Execution (15 Seconds)

### Command:
```powershell
pytest -v
```

### Expected Output:
```text
============================= 43 passed in 0.62s ==============================
```

### Closing Statement:
> *"TENDERLENS has 43 automated tests covering all 20 mandatory statutory boundary conditions, unit-rate ranking shifts, two-envelope isolation, and end-to-end integration with a 100% pass rate. Every bid evaluated. Every decision explained."*
