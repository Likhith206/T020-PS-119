# TENDERLENS — System Architecture Specification

---

## 1. Architectural Overview
**TENDERLENS** is structured as an integrated, backend-only public procurement evaluation platform designed to execute complex commercial evaluations with mathematical precision, statutory compliance, and cryptographic auditability.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COMMAND LINE INTERFACE (CLI)                    │
│      main.py (argparse, interactive subcommands, error handling)       │
└───────────────┬────────────────────────────────────────┬───────────────┘
                │                                        │
┌───────────────▼──────────────────────┐ ┌───────────────▼───────────────┐
│          MANAGEMENT SUBSYSTEM        │ │       REPORTING SUBSYSTEM     │
│   • TenderManager                    │ │   • ComparativeStatementGen   │
│   • BidderManager                    │ │   • ScorecardReporter         │
│   • EventManager                     │ │   • GraphReporter             │
│   • CSVImporter                      │ │   • ReportGenerator           │
└───────────────┬──────────────────────┘ └───────────────▲───────────────┘
                │                                        │
┌───────────────▼────────────────────────────────────────┴───────────────┐
│                    MASTER EVALUATION PIPELINE (BR-12)                   │
│                       ProcurementEvaluator                              │
├────────────────────────────────────────────────────────────────────────┤
│ • Stage 01: EMDEngine (2% cap, BG +45 days, MSE/Startup exemptions)    │
│ • Stage 02: EligibilityEngine (30% turnover, 80/50/40 experience)      │
│ • Stage 03: TechnicalEngine (60% criterion, 70% overall, Two-Envelope) │
│ • Stage 04: FinancialEngine (Unit rate over total, GST/freight norm)   │
│ • Stage 05: AbnormalBidEngine (<85% estimate, <80% avg, security calc) │
│ • Stage 06: PreferenceEngine (MSE 15%/25%, Make in India 20%/50%)      │
│ • Stage 07: RankingEngine (LCS, QCBS 70:30, SingleBid safeguards)      │
│ • Stage 08: ValidityEngine (90-day validity, 30-day extension, exit)   │
│ • Stage 09: AwardEngine (LoA, 3%/5% security, 21-day default fallback) │
└───────────────┬────────────────────────────────────────┬───────────────┘
                │                                        │
┌───────────────▼──────────────────────┐ ┌───────────────▼───────────────┐
│        INTELLIGENCE SUBSYSTEM        │ │    PROCUREMENT DECISION GRAPH │
│   • AuditEngine (SHA-256 Ledger)     │ │   • DAG Node/Edge Engine      │
│   • DecisionTrace (Explainability)   │ │   • Cascading Blockage Logic  │
│   • RiskAnalyzer (Risk Scanner)      │ │   • ASCII & JSON Exporters    │
│   • SimulationEngine (What-If Copies)│ │   • DB Graph Reconstructor    │
└───────────────┬──────────────────────┘ └───────────────┬───────────────┘
                │                                        │
┌───────────────▼────────────────────────────────────────▼───────────────┐
│                        DATA ACCESS & STORAGE LAYER                     │
│               • Database (SQLite with PRAGMA foreign_keys = ON)        │
│               • Repositories (Parameterized SQL, Strict Decimal types) │
│               • database/schema.sql (21 Normalized Relational Tables)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Decomposition

### 2.1 Storage & Repositories Layer (`src/storage/`)
- **`database.py`**: Manages SQLite connections, handles transactions with automatic commit/rollback semantics, initializes schema DDL, and provides persistent in-memory connection pooling for tests and simulations.
- **`repositories.py`**: Encapsulates data access for all 21 schema entities. Strictly converts between database strings and typed Python Decimal instances to eliminate floating-point approximation errors.

### 2.2 Core Models & Domain Layer (`src/models.py`)
- Defines pure dataclasses with `__post_init__` hooks ensuring that every monetary, percentage, and score attribute is quantized via `to_decimal()`.

### 2.3 Evaluation Engines Layer (`src/engines/`)
- Contains decoupled, single-responsibility calculation engines:
  - `emd_engine.py`: EMD rule evaluation and bank guarantee horizon analysis.
  - `eligibility_engine.py`: Multi-option past experience and turnover tests.
  - `technical_engine.py`: Weighted technical scoring and cut-off enforcement.
  - `financial_engine.py`: Commercial normalization and unit-rate arithmetic corrections.
  - `abnormal_bid_engine.py`: Strict inequality dual-threshold price analysis.
  - `preference_engine.py`: Statutory purchase preference quantity apportionments.
  - `ranking_engine.py`: LCS and QCBS ranking with multi-tier tie-breakers.
  - `validity_engine.py`: Calendar-day validity and penalty-free exit.
  - `award_engine.py`: LoA generation and performance security tracking.
  - `single_bid_engine.py`: Single-bid competition safeguards and re-tender rules.
  - `negotiation_engine.py`: Strict CVC L1-only post-tender negotiation rules.

### 2.4 Intelligence & Explainability Layer (`src/intelligence/`)
- `audit_engine.py`: Maintains a tamper-evident SHA-256 hash-linked audit chain:
  $$H_n = \text{SHA256}(H_{n-1} + \text{CanonicalJSON}(E_n))$$
- `decision_trace.py`: Reconstructs human-readable legal narratives from structured decision records.
- `risk_analyzer.py`: Automated scanning across compliance, financial, technical, timeline, and integrity risks.
- `simulator.py`: High-performance what-if simulation leveraging SQLite memory backups to leave production data unmutated.

---

## 3. Data Flow

1. **Ingestion**: CSV data parsed and validated through `CSVImporter` and `validators.py`.
2. **Registration**: Tenders and bids persisted into SQLite tables.
3. **Pipeline Execution**: `ProcurementEvaluator.evaluate_tender()` iterates through stages 1 to 9 in strict sequence according to BR-12.
4. **Decision Logging**: Every decision emits an explainable `DecisionRecord` and updates corresponding `GraphNode` and `GraphEdge`.
5. **Audit Chaining**: Major procurement events are hash-chained in `audit_events`.
6. **Reporting**: Dossiers rendered to terminal or exported as JSON.
