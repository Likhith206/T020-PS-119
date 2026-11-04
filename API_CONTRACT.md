# TENDERLENS — API Contract & Shared Interface Specification

This document defines the Python API interfaces, function signatures, parameters, return types, and exception contracts across all TENDERLENS core modules.

---

## 1. Storage & Persistence (`src/storage/`)

### `Database` (`src/storage/database.py`)
- `__init__(db_path: str = "database/tenderlens.db", schema_path: str = "database/schema.sql") -> None`
- `init_db(drop_existing: bool = False) -> None`: Initializes DDL tables, indexes, and foreign keys.
- `get_connection() -> sqlite3.Connection`: Returns connection with `PRAGMA foreign_keys = ON;` and `sqlite3.Row` factory.
- `transaction() -> Generator[sqlite3.Cursor, None, None]`: Context manager committing on success or rolling back on exception.
- `execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]`: Parameterized query execution.

---

## 2. Core Evaluator & Pipeline (`src/core/`)

### `ProcurementEvaluator` (`src/core/evaluator.py`)
- `__init__(db: Database, config_dir: str = "config") -> None`
- `evaluate_tender(tender_id: str) -> Dict[str, Any]`:
  - **Inputs**: `tender_id` (str)
  - **Outputs**: Dictionary containing `status`, `award` (`Award`), `performance_security` (`PerformanceSecurity`), `ranked_bids` (`List[Tuple[Bid, FinancialEvaluation, int]]`), and `preference_allocations` (`List[PreferenceAllocation]`).
  - **Exceptions**: `ValueError` if tender does not exist; `ValidationError` if configuration invalid.

### `ProcurementDecisionGraph` (`src/core/decision_graph.py`)
- `__init__(tender_id: str, bidder_id: Optional[str] = None, simulation_id: Optional[str] = None) -> None`
- `update_node(stage_name: str, status: str, explanation: str, calculation_details: str = "", ...) -> None`: Cascades blockage to downstream nodes on failure.
- `persist(db: Database) -> None`: Persists DAG state to SQLite tables `decision_graph_nodes` and `decision_graph_edges`.
- `reconstruct_from_db(db: Database, tender_id: str, bidder_id: Optional[str] = None) -> ProcurementDecisionGraph`: Class method restoring live graph from database.
- `render_ascii() -> str`: Renders terminal ASCII DAG diagram.
- `to_dict() -> Dict[str, Any]`: Serializes graph to JSON structure.

---

## 3. Business Rule Engines (`src/engines/`)

### `EMDEngine` (`src/engines/emd_engine.py` — BR-02)
- `calculate_required_emd(estimated_cost: Decimal) -> Decimal`: Calculates 2% of estimate capped at ₹50 Lakh.
- `evaluate(tender: Tender, bidder: Bidder, emd_record: Optional[EMDRecord], certificates: list) -> Tuple[bool, str, DecisionRecord]`:
  - Evaluates EMD payment, MSE/Startup exemptions, and 45-day BG validity horizon.

### `EligibilityEngine` (`src/engines/eligibility_engine.py` — BR-01)
- `evaluate(tender: Tender, bidder: Bidder, avg_turnover: Decimal, experiences: List[BidderExperience], certificates: List[BidderCertificate]) -> Tuple[bool, str, List[DecisionRecord]]`:
  - Evaluates 30% average turnover, 80%/50%/40% past 7-year experience, blacklisting, and MSE relaxation.

### `TechnicalEngine` (`src/engines/technical_engine.py` — BR-03)
- `evaluate(tender: Tender, bid: Bid, criteria: List[TechnicalCriterion], scores: List[TechnicalScore]) -> Tuple[bool, Decimal, Dict[str, Decimal], List[DecisionRecord]]`:
  - Evaluates weighted evaluator scores against 60% individual and 70% overall cut-offs.

### `FinancialEngine` (`src/engines/financial_engine.py` — BR-04)
- `evaluate(tender: Tender, bid: Bid, schedule_items: List[PriceScheduleItem], correction_accepted: bool = True) -> Tuple[FinancialEvaluation, List[DecisionRecord]]`:
  - Enforces unit-rate precedence over totals (`Qty * Unit Rate`), adds missing taxes/freight.
  - **Exceptions**: Raises `TwoEnvelopeViolationError` if bidder is `NON_RESPONSIVE` or `TECHNICALLY_DISQUALIFIED`.

### `AbnormalBidEngine` (`src/engines/abnormal_bid_engine.py` — BR-07)
- `analyze_bid(tender: Tender, bid: Bid, evaluation: FinancialEvaluation, all_qualified_evals: List[FinancialEvaluation], justification_status: Optional[str] = "ACCEPTED") -> Tuple[bool, bool, Decimal, DecisionRecord]`:
  - Evaluates strict inequality: Price < 85% of estimate OR Price < 80% of average qualified bid price. Computes additional performance security.

### `PreferenceEngine` (`src/engines/preference_engine.py` — BR-05)
- `evaluate_preferences(tender: Tender, l1_bid: Bid, l1_eval: FinancialEvaluation, other_evals: list) -> Tuple[List[PreferenceAllocation], List[DecisionRecord]]`:
  - Applies MSE 15% price margin / 25% quantity split and Class-I 20% margin / 50% split. Handles 100% reserved items.

### `RankingEngine` (`src/engines/ranking_engine.py` — BR-06)
- `rank_bids(tender: Tender, qualified_bids: List[Tuple[Bid, FinancialEvaluation]]) -> Tuple[List[Tuple[Bid, FinancialEvaluation, int]], List[DecisionRecord]]`:
  - Ranks bids under LCS or QCBS (70:30 inverse proportional scoring) with multi-tier tie-breakers.

### `ValidityEngine` (`src/engines/validity_engine.py` — BR-08)
- `evaluate_validity(tender: Tender, bid: Bid, as_of_date: Optional[str] = None, extension_response: Optional[str] = None) -> Tuple[bool, str, str, DecisionRecord]`:
  - Evaluates 90-day base validity, 30-day extension, and penalty-free exit upon refusal.

### `AwardEngine` (`src/engines/award_engine.py` — BR-09)
- `create_award(tender: Tender, winning_bid: Bid, evaluation: FinancialEvaluation, loa_date: Optional[str] = None) -> Tuple[Award, PerformanceSecurity, DecisionRecord]`:
  - Issues LoA and calculates standard 3% (or abnormal 5% + additional) security due in 21 days.
- `process_security_default(tender: Tender, award: Award, l1_price: Decimal, next_ranked_bid: Optional[Bid], next_eval: Optional[FinancialEvaluation]) -> Tuple[str, str, DecisionRecord]`:
  - Manages forfeiture and evaluates fallback to next bidder if within 10% of L1.

### `SingleBidEngine` (`src/engines/single_bid_engine.py` — BR-10)
- `evaluate_competition(tender: Tender, responsive_bids: List[Bid]) -> Tuple[bool, str, DecisionRecord]`:
  - Restricts single-bid award unless `single_bid_allowed` is enabled; otherwise triggers re-tender.

### `NegotiationEngine` (`src/engines/negotiation_engine.py` — BR-11)
- `evaluate_negotiation_eligibility(tender: Tender, bid: Bid, evaluation: FinancialEvaluation, is_l1: bool) -> Tuple[bool, str, Decimal, DecisionRecord]`:
  - Enforces CVC norms: negotiation permitted strictly with L1 when price exceeds estimate by >10%.

---

## 4. Intelligence & Audit Subsystems (`src/intelligence/`)

### `AuditEngine` (`src/intelligence/audit_engine.py`)
- `log_event(tender_id: str, event_type: str, event_details: Dict[str, Any], bidder_id: Optional[str] = None) -> AuditEvent`: Appends SHA-256 hash-linked record.
- `verify_chain(tender_id: str) -> Tuple[bool, List[str]]`: Cryptographically walks the chain, re-computing each SHA-256 link.

### `RiskAnalyzer` (`src/intelligence/risk_analyzer.py`)
- `scan_risks(tender: Tender) -> List[RiskRecord]`: Scans systemic and bidder vulnerabilities across compliance, financial, technical, timeline, and integrity categories.

### `SimulationEngine` (`src/intelligence/simulator.py`)
- `run_simulation(tender_id: str, scenario: str) -> Dict[str, Any]`: Executes what-if scenario in an isolated in-memory database clone.

---

## 5. Domain Exceptions
- `ValidationError`: Raised on malformed configuration, corrupt CSV data, or invalid dates.
- `TwoEnvelopeViolationError`: Raised on unauthorized access to the financial envelope of an unqualified bidder.
- `AuditVerificationError`: Raised upon cryptographic hash-chain discontinuity.
