# TENDERLENS — Explainable & Intelligent Procurement Evaluation Engine
### Problem Statement: PS-119 | Public Services — Procurement
**Tagline:** *Every Bid Evaluated. Every Decision Explained.*

---

## 1. Project Overview

**TENDERLENS** is an integrated, explainable backend procurement evaluation engine built in Python and SQLite to automate public procurement evaluations under Indian General Financial Rules (GFR 2017) and CVC guidelines. By formalizing evaluations into a **Procurement Decision Graph (DAG)**, coupling every determination to structured mathematical proofs, securing the timeline with a **tamper-evident SHA-256 audit ledger**, and enforcing **strict Two-Envelope financial protection**, TENDERLENS replaces opaque evaluation spreadsheets with a transparent, legally defensible system.

---

## 2. Core Distinctive Features

1. **Procurement Decision Graph (DAG)**:
   - Formulates the 9 evaluation stages as an explicit directed acyclic graph.
   - Enforces cascading blockage: if an upstream stage fails (e.g. Stage 1 EMD or Stage 3 Technical), all downstream stages are immediately marked `BLOCKED`.
   - Graph state is persisted to SQLite and reconstructed dynamically via terminal ASCII or JSON.

2. **Explainable Decision Engine**:
   - Every rule execution generates a structured `DecisionRecord` containing input snapshots, required thresholds, exact mathematical calculation steps, human-readable explanations, and evidence citations.

3. **Tamper-Evident SHA-256 Audit Ledger**:
   - Cryptographically links all procurement state transitions:
     $$H_n = \text{SHA256}(H_{n-1} + \text{CanonicalJSON}(E_n))$$
   - Anchored to a defined 64-zero genesis hash. The `audit-verify` command recalculates the chain, detecting modified, deleted, or re-ordered events.

4. **Isolated What-If Simulation Sandbox**:
   - Evaluates procurement contingencies (L1 bidder withdrawal, MSE price matching, security defaults) on an in-memory clone of the database.
   - Generates differential outcome reports and simulated decision graphs while leaving production data 100% untouched.

5. **Strict Two-Envelope Financial Protection**:
   - Prevents premature access to commercial price schedules.
   - If a bidder is not `RESPONSIVE` and `QUALIFIED`, any financial evaluation attempt raises a `TwoEnvelopeViolationError`.

6. **Pure Decimal Computational Architecture**:
   - Zero floating-point representation (`float`) in financial, percentage, or score computations.
   - Strictly uses Python's `decimal.Decimal` with round-half-up quantization.

7. **Multi-Category Procurement Risk Intelligence**:
   - Automatically scans active tenders for compliance, financial, technical, timeline, and integrity vulnerabilities.

8. **Configurable Business Rule Engine**:
   - All statutory percentages, cut-offs, and thresholds are managed via structured JSON files (`config/`) validated at startup.

---

## 3. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.10+ (Tested on Python 3.14.3) | Clean, robust standard library (`decimal`, `hashlib`, `sqlite3`, `argparse`) |
| **Database** | SQLite (with `PRAGMA foreign_keys = ON;`) | 21 normalized relational tables, zero external database setup |
| **Monetary Math** | `decimal.Decimal` (ROUND_HALF_UP) | Eliminates IEEE-754 floating-point rounding errors |
| **Audit Hashing** | SHA-256 | Cryptographic tamper-evidence for procurement events |
| **Input Format** | CSV | Standard format for government tender and bid imports |
| **Configuration** | JSON | Startup-validated thresholds without code hardcoding |
| **Testing** | pytest 9.2.0 | Comprehensive unit, boundary, simulation, and integration tests |
| **CLI** | `argparse` | Pure terminal-based interface (No frontend / web dependencies) |

---

## 4. Business Rule Precedence (BR-12)

TENDERLENS evaluates every tender through the following mandatory 9-stage sequence:

```
01. TIMELINE & EMD (BR-02) ─────────► 2% rate capped at ₹50L, 45-day BG validity horizon, MSE exemptions
         │
02. ELIGIBILITY (BR-01) ────────────► 30% turnover boundary, 80%/50%/40% 7-year experience, blacklist check
         │
03. TECHNICAL EVALUATION (BR-03) ───► 60% individual & 70% overall cut-offs [TWO-ENVELOPE SECURITY GATE]
         │
04. FINANCIAL EVALUATION (BR-04) ───► Unit-rate arithmetic corrections (Qty × Rate) & tax normalization
         │
05. ABNORMAL BID ANALYSIS (BR-07) ──► Strict inequality (<85% estimate, <80% avg) & additional security
         │
06. PREFERENCES (BR-05) ────────────► MSE 15% margin / 25% split, Make in India 20% / 50%, reserved items
         │
07. RANKING (BR-06, BR-10) ─────────► LCS or QCBS (70:30 composite scoring), single-bid safeguards
         │
08. BID VALIDITY (BR-08) ───────────► 90-day base validity, 30-day extension, penalty-free exit
         │
09. AWARD & SECURITY (BR-09, BR-11) ► LoA issuance, 3%/5% security, 21-day default fallback, L1 negotiation
```

---

## 5. Installation & Environment Setup

### 5.1 Clone Repository
```powershell
git clone https://github.com/Likhith206/T020-PS-119.git
cd T020-PS-119
```

### 5.2 Activate Virtual Environment
```powershell
# Using the pre-configured Python 3.14 virtual environment:
.\.venv\Scripts\Activate.ps1
```

### 5.3 Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 6. Complete CLI Command Reference

### Database Initialization
```powershell
# Initialize SQLite database schema
python main.py init-db

# Reset and recreate clean database
python main.py init-db --reset
```

### Tender Management & Bid Registration
```powershell
# Create tenders from CSV
python main.py create-tender --file data/input/tenders.csv

# List registered tenders
python main.py list-tenders

# Import bids and credential schedules for a tender
python main.py import-bids --tender TND001 --file data/input/bids.csv

# List registered bids for a tender
python main.py list-bids TND001
```

### Evaluation & Dossier Reporting
```powershell
# Execute complete BR-12 evaluation pipeline
python main.py evaluate TND001

# Display consolidated procurement evaluation report
python main.py report TND001

# Display technical evaluation scorecard for a bidder
python main.py scorecard TND001 BDR001
```

### Explainability & Decision Graph
```powershell
# Display explainable decision trace for a bidder
python main.py explain TND001 BDR001

# Display decision trace for a specific evaluation stage
python main.py explain-stage TND001 BDR001 technical

# Render Procurement Decision Graph (ASCII view)
python main.py decision-graph TND001 --bidder BDR001

# Render Decision Graph in JSON format
python main.py decision-graph TND001 --bidder BDR001 --format json
```

### Audit & Security
```powershell
# Display chronological hash-linked audit ledger
python main.py audit TND001

# Cryptographically verify SHA-256 audit chain integrity
python main.py audit-verify TND001
```

### Intelligence, Simulation & Award
```powershell
# Scan procurement risk intelligence
python main.py risks TND001

# Run isolated What-If scenario simulation
python main.py simulate TND001 --scenario l1_withdrawal
python main.py simulate TND001 --scenario mse_match
python main.py simulate TND001 --scenario security_failure
python main.py simulate TND001 --scenario abnormal_rejection

# Display final contract award details
python main.py award TND001
```

---

## 7. Automated Test Suite

TENDERLENS includes **43 automated pytest tests** covering all 20 mandatory statutory boundary conditions, unit-rate ranking inversions, two-envelope isolation, and end-to-end integration:

```powershell
# Run the complete test suite
pytest -v
```

### Verification Highlights:
- **Turnover exactly 30%**: `test_turnover_boundary_exactly_30_percent_passes` (PASS)
- **BG validity exactly 45 days beyond bid validity**: `test_emd_boundary_exactly_45_days_passes` (PASS)
- **Individual technical score exactly 60%**: `test_technical_boundary_exact_60_individual_and_70_overall_passes` (PASS)
- **Overall technical score exactly 70%**: `test_technical_boundary_exact_60_individual_and_70_overall_passes` (PASS)
- **MSE bid exactly 15% above L1**: `test_mse_boundary_exact_15_percent_qualifies` (PASS)
- **Unit-rate correction changes L1**: `test_unit_rate_correction_changes_l1` (PASS)
- **Price exactly 85% of estimate**: `test_abnormal_boundary_exact_85_percent_does_not_trigger` (PASS)
- **Audit ledger tampering detection**: `test_audit_detects_data_tampering` (PASS)
- **What-if simulation isolation**: `test_simulation_complete_isolation` (PASS)

---

## 8. Project Structure

```
T020-PS-119/
├── main.py                     # Unified CLI Application (16 subcommands)
├── requirements.txt            # Python Dependencies
├── README.md                   # System Documentation
├── API_CONTRACT.md             # Shared Interfaces & Type Signatures
├── PROJECT_PLAN.md             # Development Stages & Milestones
├── TASK_BOARD.md               # Feature & Task Tracking Board
├── TEAM_WORKFLOW.md            # Unified Ownership & Engineering Standards
├── DECISION_LOG.md             # Architecture Decisions & Statutory Assumptions
├── ORIGINALITY_AND_DESIGN_DECISIONS.md # Engineering Originality Rationale
│
├── config/                     # Startup-Validated Configuration
│   ├── settings.json
│   ├── business_rules.json
│   └── scoring_defaults.json
│
├── data/
│   ├── input/                  # Synthetic Demonstration Datasets
│   │   ├── tenders.csv
│   │   ├── bids.csv
│   │   ├── experience.csv
│   │   ├── certificates.csv
│   │   ├── emd.csv
│   │   ├── technical_scores.csv
│   │   └── price_schedules.csv
│   └── sample/                 # Mirrored Sample Data
│
├── database/
│   ├── schema.sql              # 21 Normalized Relational SQLite Tables
│   └── tenderlens.db           # SQLite Database File
│
├── src/
│   ├── models.py               # Typed Domain Models with Decimal Quantization
│   │
│   ├── core/
│   │   ├── decision_graph.py   # Procurement Decision Graph (DAG & Blockage)
│   │   ├── evaluator.py        # Master Evaluation Pipeline (BR-12)
│   │   ├── pipeline.py         # Pipeline Wrapper
│   │   └── rule_engine.py      # Rule Registry & Metadata
│   │
│   ├── engines/
│   │   ├── abnormal_bid_engine.py  # Strict Inequality Low Bid Analysis (BR-07)
│   │   ├── award_engine.py         # LoA & 21-Day Security Management (BR-09)
│   │   ├── eligibility_engine.py   # 30% Turnover & 7-Yr Experience (BR-01)
│   │   ├── emd_engine.py           # 2% Cap, 45-Day BG & Exemptions (BR-02)
│   │   ├── financial_engine.py     # Unit-Rate Arithmetic & Normalization (BR-04)
│   │   ├── negotiation_engine.py   # CVC L1-Only Price Negotiation (BR-11)
│   │   ├── preference_engine.py    # MSE 15%/25% & Class-I 20%/50% Splits (BR-05)
│   │   ├── ranking_engine.py       # LCS & QCBS 70:30 Ranking (BR-06)
│   │   ├── single_bid_engine.py    # Single-Bid Competition Safeguards (BR-10)
│   │   └── validity_engine.py      # 90-Day Validity & Penalty-Free Exit (BR-08)
│   │
│   ├── intelligence/
│   │   ├── audit_engine.py     # Tamper-Evident SHA-256 Hash Chain
│   │   ├── decision_trace.py   # Explainable Legal Narrative Generator
│   │   ├── risk_analyzer.py    # Multi-Category Risk Intelligence Scanner
│   │   └── simulator.py        # In-Memory Database Contingency Sandbox
│   │
│   ├── managers/
│   │   ├── bidder_manager.py   # Bidder & Bid Lifecycle Manager
│   │   ├── event_manager.py    # Procurement Milestone Event Tracker
│   │   └── tender_manager.py   # Tender Criteria & Status Manager
│   │
│   ├── reporting/
│   │   ├── comparative_statement.py # Financial Comparative Statement Generator
│   │   ├── graph_reporter.py        # Decision Graph Renderer
│   │   ├── report_generator.py      # Consolidated Dossier Generator
│   │   └── scorecard.py             # Technical Evaluation Scorecard Reporter
│   │
│   ├── storage/
│   │   ├── database.py         # SQLite Connection & Transaction Manager
│   │   └── repositories.py     # 21 Normalized Repositories (Parameterized SQL)
│   │
│   └── utils/
│       ├── csv_importer.py     # Schema-Validated CSV Ingestion
│       ├── date_utils.py       # Calendar-Day Standardized Date Arithmetic
│       ├── money_utils.py      # High-Precision Decimal Math & INR Formatting
│       └── validators.py       # Startup Config & CSV Header Validators
│
├── tests/                      # 43 Automated Pytest Tests (100% Pass Rate)
│   ├── conftest.py
│   ├── test_abnormal_bid.py
│   ├── test_audit.py
│   ├── test_award.py
│   ├── test_decision_graph.py
│   ├── test_edge_cases.py
│   ├── test_eligibility.py
│   ├── test_emd.py
│   ├── test_financial.py
│   ├── test_integration.py
│   ├── test_preferences.py
│   ├── test_ranking.py
│   ├── test_risk.py
│   ├── test_simulator.py
│   ├── test_technical.py
│   └── test_validity.py
│
├── docs/                       # Complete Engineering Documentation
│   ├── BUSINESS_RULES.md       # Full Specification of BR-01 to BR-12
│   ├── DATABASE_DESIGN.md      # Schema, Types, Constraints & ER Diagram
│   ├── DECISION_GRAPH_DESIGN.md# Computable DAG Architecture & Blockage
│   ├── DESIGN_DOCUMENT.md      # Complete System Design Document
│   ├── SYSTEM_ARCHITECTURE.md  # Layered Decomposition & Interfaces
│   └── TESTING_STRATEGY.md     # Test Coverage & Boundary Case Matrix
│
└── demo/
    └── DEMO_SCRIPT.md          # 5-Minute Live Faculty Demonstration Script
```

---

## 9. Assumptions & Statutory Ambiguities

As documented in `DECISION_LOG.md`:
1. **Abnormal Low Bid Additional Security**: Calculated as `Shortfall % = ((0.85 × Estimate) - Price) / Estimate × 100` applied to contract value.
2. **Next-Ranked Bidder 10% Margin**: Measured against the **L1 evaluated price** (`L2 Price <= L1 × 1.10`).
3. **QCBS Statutory Preferences**: Margin bands calculated against the lowest evaluated commercial price among qualified bidders.
4. **Arithmetic Precedence**: Quoted unit rate strictly governs over totals (`Quantity × Unit Rate`).
5. **Calendar Inclusivity**: Day 90 is inclusive and legally valid for award actions.
6. **Single-Bid Re-tender**: Mandatory re-tender unless `single_bid_allowed` is explicitly enabled.
7. **100% Reserved Items**: 100% quantity allocated exclusively to eligible MSE at matched L1 price.

---

## 10. Limitations

- **Single-Lot Price Schedules**: The current commercial normalization engine evaluates single-lot price schedules; multi-lot package optimization will be introduced in future releases.
- **Local Hash Chain**: SHA-256 hash chaining ensures cryptographic tamper evidence against database manipulation; external distributed ledger anchoring can be added for absolute non-repudiation.
