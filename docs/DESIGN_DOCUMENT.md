# TENDERLENS — Comprehensive System Design Document
## PS-119: Explainable & Intelligent Procurement Evaluation Engine
### Tagline: Every Bid Evaluated. Every Decision Explained.

---

## 1. Abstract
**TENDERLENS** is an integrated, explainable backend procurement evaluation engine built in Python and SQLite to automate public procurement evaluations under Indian General Financial Rules (GFR 2017) and CVC guidelines. By formalizing evaluations into a **Procurement Decision Graph (DAG)**, coupling every determination to structured mathematical proofs, securing the timeline with a **tamper-evident SHA-256 audit ledger**, and enforcing **strict Two-Envelope financial protection**, TENDERLENS replaces opaque evaluation spreadsheets with a transparent, legally defensible system.

---

## 2. Problem Definition & Objectives
Traditional tender evaluations suffer from:
- Delays and administrative bottlenecks in verifying eligibility, turnover, and past credentials.
- Arithmetic inconsistencies where line-item quantities and rates do not match quoted totals.
- Vulnerability to premature disclosure of financial envelopes before technical qualification.
- Legal disputes arising from opaque discretionary disqualifications without verifiable evidence.
- Difficulty simulating contingencies (e.g. L1 withdrawal, price matching) without risking data contamination.

### Core Objectives:
1. Automate statutory evaluation across all 9 procurement stages with strict rule precedence (BR-12).
2. Generate computable, reconstructable **Procurement Decision Graphs** reflecting real execution state.
3. Guarantee that financial envelopes remain locked for technically disqualified bidders.
4. Provide a tamper-evident audit ledger verifying complete chain integrity via SHA-256.
5. Enable isolated scenario simulation that leaves official procurement records completely unmutated.

---

## 3. Functional Requirements Overview
- **FR-01: Tender Management**: Lifecycle tracking, LCS/QCBS modes, MSE relaxation, single-bid flags.
- **FR-02: Bidder & Bid Registration**: Two-envelope separation, credential tracking, blacklisting status.
- **FR-03: Eligibility Evaluation (BR-01)**: 30% turnover boundary, 80%/50%/40% 7-year experience rules.
- **FR-04: EMD Validation (BR-02)**: 2% rate capped at ₹50 Lakh, 45-day BG horizon, MSE/Startup exemptions.
- **FR-05: Technical Scoring (BR-03)**: Weighted evaluation, 60% individual & 70% overall cut-offs.
- **FR-06: Financial Normalization (BR-04)**: Unit-rate precedence, all-inclusive delivered price basis.
- **FR-07: Procurement Preferences (BR-05)**: MSE 15%/25% split, Make in India 20%/50% split, reserved items.
- **FR-08: Competitive Ranking (BR-06)**: LCS price ranking, QCBS 70:30 composite inverse scoring.
- **FR-09: Abnormally Low Bids (BR-07)**: Strict inequality (<85% estimate, <80% avg), additional security.
- **FR-10: Validity & Extensions (BR-08)**: 90-day base, single 30-day extension, penalty-free exit.
- **FR-11: Award & Performance Security (BR-09)**: LoA, 3% vs 5% security, 21-day default fallback.
- **FR-12: Competition Safeguards (BR-10)**: Single-bid re-tender rules.
- **FR-13: Price Negotiation Protocol (BR-11)**: Strict L1-only negotiation when > 10% excess.
- **FR-14: Consolidated Reporting**: Comprehensive comparative dossiers, scorecards, and audit trails.

---

## 4. Non-Functional & Security Requirements
1. **Mathematical Exactitude**: Zero floating-point representation (`float`) in financial, percentage, or score computations. All numbers use `decimal.Decimal` with round-half-up quantization.
2. **Relational Integrity**: Enforced foreign keys across all 21 tables. Parameterized SQL prevents SQL injection.
3. **Cryptographic Tamper-Evidence**: Chronological SHA-256 hash chaining of procurement events.
4. **Platform Compatibility**: Pure Python backend tested on Windows with Python 3.14.3.
5. **Zero External Frontend Dependencies**: Pure CLI interface operated entirely from the integrated terminal.

---

## 5. Decision Graph & Explainability Architecture
Every stage transition evaluates explicit preconditions. If a gate fails, downstream nodes are placed into a `BLOCKED` state. Structured decision records capture:
- Rule ID (e.g., `BR-01`, `BR-03`, `BR-07`)
- Stage Name
- Input Snapshot (raw parameters)
- Required Thresholds
- Mathematical Calculation Steps
- Human-Readable Legal Narrative
- Evidence Reference

---

## 6. Known Limitations & Future Enhancements
- **Multi-Lot Splitting**: Current implementation supports single-lot commercial schedules; future iterations will support multi-lot scheduling.
- **Distributed Ledger Anchoring**: The local SHA-256 hash chain provides tamper evidence; anchoring root hashes to an external timestamping authority or public blockchain will provide proof against root-level history rewriting.
