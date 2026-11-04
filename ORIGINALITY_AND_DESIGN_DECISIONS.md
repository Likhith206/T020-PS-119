# TENDERLENS — Originality & Distinctive Design Decisions

---

## 1. Statement of Genuine Engineering Originality

**TENDERLENS** was developed through an independent architectural conception to address the systemic vulnerabilities of public procurement evaluation engines. Rather than adapting generic boilerplate or superficial scripts, TENDERLENS integrates eight distinctive engineering concepts into a unified product.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TENDERLENS INNOVATION MATRIX                    │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. Procurement Decision Graph  │ Formal DAG with cascading blockage   │
│ 2. Explainable Rule Engine     │ Rule-by-rule mathematical proofs     │
│ 3. Tamper-Evident Ledger       │ SHA-256 hash-chained event integrity  │
│ 4. Isolated What-If Simulator  │ In-memory clone contingency sandbox  │
│ 5. Risk Intelligence Subsystem │ Multi-category vulnerability scanner  │
│ 6. Central Config Engine       │ Versioned thresholds without hardcode │
│ 7. Two-Envelope Guard          │ Logical & physical price separation   │
│ 8. Reconstructable History     │ Full SQLite graph and state replay   │
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 2. Distinctive Architectural Choices & Alternatives Considered

### Feature 1: Procurement Decision Graph (DAG)
- **Traditional Approach Considered**: Nested `if/else` control flow or procedural Python scripts.
- **Why Rejected**: Procedural scripts make it difficult to determine at what exact point downstream stages should be blocked, cannot be persisted as a clean data structure, and cannot be audited retroactively.
- **TENDERLENS Innovation**: Modeled as an explicit 9-node DAG (`decision_graph_nodes`, `decision_graph_edges`). When an upstream node fails (e.g. Stage 1 EMD or Stage 3 Technical), a cascading blockage algorithm automatically flags downstream stages as `BLOCKED`. The graph is stored in SQLite and can be replayed via ASCII or JSON.

### Feature 2: Explainable Rule Execution Engine
- **Traditional Approach Considered**: Printing hardcoded log strings or raising generic exceptions.
- **Why Rejected**: Violates natural justice principles in public procurement. When a vendor is disqualified, the procuring authority must provide exact mathematical reasons and evidence citations.
- **TENDERLENS Innovation**: Every evaluation rule emits a typed `DecisionRecord` containing input snapshots, threshold values, step-by-step arithmetic, result (`PASS`/`FAIL`/`WARNING`/`BLOCKED`), and evidence references. Accessible via `python main.py explain <TENDER> <BIDDER>`.

### Feature 3: Tamper-Evident SHA-256 Audit Ledger
- **Traditional Approach Considered**: Standard application logging to a plain text file.
- **Why Rejected**: Plain log files can be modified or deleted without detection.
- **TENDERLENS Innovation**: Each procurement event is cryptographically hash-chained:
  $$H_n = \text{SHA256}(H_{n-1} + \text{CanonicalJSON}(E_n))$$
  Anchored to a 64-zero genesis hash. The `audit-verify` command recalculates every link in sequence, immediately pinpointing modified, inserted, re-ordered, or deleted records.

### Feature 4: Memory-Isolated What-If Simulation Sandbox
- **Traditional Approach Considered**: Modifying production database rows inside an uncommitted transaction and calling `rollback()`, or creating duplicated shadow database files.
- **Why Rejected**: Uncommitted transactions risk locking production SQLite databases or accidentally committing during connection teardown. Shadow files leave stale disk artifacts.
- **TENDERLENS Innovation**: Uses `sqlite3.Connection.backup()` to create an instant in-memory copy of the database. The scenario (e.g., L1 withdrawal, MSE match, performance default) executes entirely inside RAM, produces a comparative diff report and simulation decision graph, and leaves production data 100% untouched.

### Feature 5: Multi-Category Risk Intelligence
- **Traditional Approach Considered**: Relying exclusively on manual administrative scrutiny.
- **Why Rejected**: Sub-threshold risks (such as technical scores barely clearing the 70% cutoff by 0.5%, or BG validity expiring 10 days after tender closing) often go unnoticed until disputes arise.
- **TENDERLENS Innovation**: Automated background scanner evaluating 5 distinct risk vectors: `COMPLIANCE`, `FINANCIAL`, `TECHNICAL`, `TIMELINE`, and `INTEGRITY`, categorizing findings from `LOW` to `CRITICAL` with suggested administrative actions.

### Feature 6: Centralized Versioned Configuration Engine
- **Traditional Approach Considered**: Hardcoding 30% turnover, 2% EMD, or 70% technical cutoff directly into Python functions.
- **Why Rejected**: Makes policy updates dangerous and untraceable.
- **TENDERLENS Innovation**: Structured JSON configurations (`settings.json`, `business_rules.json`, `scoring_defaults.json`) validated at application startup. If a required threshold is missing or weights do not sum to 100%, the application fails fast rather than silently applying arbitrary defaults.

### Feature 7: Strict Two-Envelope Cryptographic/Logical Guard
- **Traditional Approach Considered**: Loading the entire bid object with price schedule into memory and simply not printing the price.
- **Why Rejected**: In-memory availability violates the legal principle that price envelopes must remain strictly unopened until technical qualification is gazetted.
- **TENDERLENS Innovation**: `FinancialEngine.evaluate()` explicitly checks `bid.technical_status == "QUALIFIED"` and `bid.responsiveness_status == "RESPONSIVE"`. If violated, it raises `TwoEnvelopeViolationError` before reading price schedules.

### Feature 8: Pure Decimal Computational Architecture
- **Traditional Approach Considered**: Standard Python `float`.
- **Why Rejected**: Floating point IEEE-754 representation induces rounding drift on large contract sums (e.g. 50 crore INR).
- **TENDERLENS Innovation**: Exclusively uses `decimal.Decimal` with round-half-up quantization across every monetary calculation, unit rate multiplication, and QCBS formula.
