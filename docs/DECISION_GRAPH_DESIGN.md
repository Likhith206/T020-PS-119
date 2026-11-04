# TENDERLENS — Procurement Decision Graph Design Specification
## Primary Engineering Differentiator

The **Procurement Decision Graph** is the central architectural pillar of TENDERLENS. Rather than executing business logic as opaque scripts or disjointed procedural code, TENDERLENS models public procurement evaluation as a formal, computable **Directed Acyclic Graph (DAG)** of decision nodes and dependency edges.

---

## 1. Architectural Philosophy
In public procurement disputes (e.g., writ petitions, administrative appeals, anti-corruption inquiries), the primary legal question is rarely just *"What was the outcome?"* but rather:
1. *On what exact date and evidence was a bidder disqualified?*
2. *Were subsequent stages properly barred or did unauthorized parties peek at financial bids?*
3. *Can the entire chain of determinations be mathematically replayed and verified?*

The Procurement Decision Graph provides this structural guarantee by binding stage execution directly to explicit dependency rules.

---

## 2. Graph Taxonomy & Pipeline Stages

```
[01. TIMELINE & EMD]
         │ (Must Pass EMD & BG horizon)
         ▼
[02. ELIGIBILITY]
         │ (Must Pass Turnover, Experience, Blacklist check)
         ▼
[03. TECHNICAL EVALUATION]
         │ (Must Pass 60% individual & 70% overall cut-offs)
         ▼  [Two-Envelope Security Barrier]
[04. FINANCIAL EVALUATION]
         │ (Must complete arithmetic unit-rate corrections & tax normalization)
         ▼
[05. ABNORMAL BID ANALYSIS]
         │ (Rate justification accepted or additional security imposed)
         ▼
[06. PROCUREMENT PREFERENCES]
         │ (MSE 15%/25% and Make-in-India 20%/50% splits evaluated)
         ▼
[07. RANKING (LCS / QCBS)]
         │ (Competitive ranking assigned; single-bid safeguards checked)
         ▼
[08. BID VALIDITY]
         │ (Legally enforceable within 90-day base or 30-day extension)
         ▼
[09. AWARD & PERFORMANCE SECURITY]
         (LoA issued, 3%/5% security tracked, fallback or negotiation evaluated)
```

---

## 3. Node & Edge Data Structures

### Decision Node (`decision_graph_nodes` Table)
| Field | Type | Description |
|---|---|---|
| `node_id` | TEXT PK | Unique identifier (e.g., `ND_TND001_BID001_TECHNICAL_EVALUATION`) |
| `tender_id` | TEXT FK | Reference to parent tender |
| `bidder_id` | TEXT FK | Target bidder (or `NULL` for tender-level aggregate nodes) |
| `stage_name` | TEXT | Canonical stage name from sequence |
| `stage_order` | INTEGER | Sequence order (1 to 9) |
| `business_rule_ids`| TEXT | JSON array of associated rule identifiers (e.g. `["BR-03"]`) |
| `execution_status` | TEXT | `PENDING`, `RUNNING`, `PASSED`, `FAILED`, `WARNING`, `BLOCKED`, `SKIPPED` |
| `input_snapshot` | TEXT | JSON snapshot of input parameters evaluated |
| `output_snapshot`| TEXT | JSON snapshot of derived calculations and ratings |
| `calculation_details`| TEXT | Exact mathematical calculation string |
| `decision_explanation`| TEXT | Human-readable legal rationale |
| `evidence_reference`| TEXT | Audit trail document reference |
| `execution_timestamp`| TEXT | ISO-8601 UTC timestamp of execution |
| `is_simulation` | INTEGER | Boolean flag indicating isolated simulation run |
| `simulation_id` | TEXT | Unique simulation session identifier if simulated |

### Dependency Edge (`decision_graph_edges` Table)
| Field | Type | Description |
|---|---|---|
| `edge_id` | TEXT PK | Unique edge identifier |
| `tender_id` | TEXT FK | Parent tender |
| `source_node_id` | TEXT FK | Predecessor node |
| `target_node_id` | TEXT FK | Successor node |
| `dependency_condition` | TEXT | Condition expression (e.g., `"TIMELINE_AND_EMD MUST PASS"`) |
| `dependency_result` | TEXT | `SATISFIED`, `UNSATISFIED`, or `BLOCKED` |
| `explanation` | TEXT | Descriptive reason for dependency link |

---

## 4. Execution State Machine & Cascading Blockage

The graph state machine supports 7 definitive lifecycle states:

```
[PENDING] ──> [RUNNING] ──┬──> [PASSED]
                          ├──> [WARNING]
                          ├──> [SKIPPED]
                          └──> [FAILED]
                                  │
                                  ▼ (Cascades downstream)
                             [BLOCKED]
```

### Cascading Blockage Algorithm
When any node transitions to `FAILED`:
1. The engine identifies the node's `stage_order`.
2. All successor nodes with higher `stage_order` are immediately set to `BLOCKED`.
3. Edge states are set to `UNSATISFIED`.
4. The financial envelope remains physically unopened for technically disqualified bids.

---

## 5. Persistence & Reconstruction
The decision graph is saved to SQLite upon evaluation.
- When `python main.py decision-graph TND001 --bidder BID001` is run, the engine executes `ProcurementDecisionGraph.reconstruct_from_db()`.
- Nodes and edges are rehydrated from stored tables.
- Renders live ASCII or JSON representations without relying on volatile in-memory cache.

---

## 6. Simulation Isolation
In what-if scenarios (e.g. L1 withdrawal, price shifts), a separate simulation graph is created with `is_simulation = 1` and a distinct `simulation_id`. Official graph nodes and official records remain 100% immutable.
