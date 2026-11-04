# TENDERLENS — Architecture Decision Log & Explicit Assumptions

This document formally records all design decisions, trade-offs, and procurement domain assumptions implemented in **TENDERLENS**.

---

## 1. Architectural Decisions

### ADR-01: Pure Decimal Financial Computing
- **Decision**: All financial amounts, tax calculations, percentage splits, and scores must strictly use Python `decimal.Decimal` with explicit `ROUND_HALF_UP` quantization.
- **Rationale**: IEEE-754 binary floating-point numbers introduce minute representation errors (e.g., `0.1 + 0.2 != 0.3`). In public procurement tenders worth hundreds of crores, fractional rounding errors could incorrectly shift L1 rankings and cause legal challenges.
- **Consequences**: Zero floating point values in memory or in database queries. Database stores monetary amounts as strings.

### ADR-02: Procurement Decision Graph (DAG) as Core Engine
- **Decision**: Model the 9 stages of procurement evaluation as an explicit directed acyclic graph with dependency edges and cascading blockage rules.
- **Rationale**: Replaces opaque procedural scripting with an inspectable data structure that can be persisted in SQLite and mathematically reconstructed for audits or court hearings.
- **Consequences**: Enables immediate visual tracing of why a bidder was disqualified and which downstream stages were blocked.

### ADR-03: Two-Envelope Cryptographic/Logical Gate
- **Decision**: Enforce an unyielding gate: if a bidder fails responsiveness or technical evaluation, the financial envelope remains strictly locked (`financial_envelope_opened = False`). Any invocation of `FinancialEngine.evaluate()` raises `TwoEnvelopeViolationError`.
- **Rationale**: Under Indian procurement law, opening a disqualified bidder's price schedule violates tender sanctity and invites accusations of bid tampering or bias.

### ADR-04: Isolated What-If Simulation via SQLite In-Memory Clones
- **Decision**: Perform simulations (L1 withdrawal, MSE matching, default fallbacks) on an in-memory clone of the database created via `sqlite3.Connection.backup()`.
- **Rationale**: Guarantees zero risk of accidental mutation or contamination of production procurement records or audit chains.

---

## 2. Explicit Domain Assumptions (Addressing Statutory Ambiguities)

### Assumption 1: Additional Performance Security Formula for Abnormally Low Bids
- **Context**: GFR Rule 144(xi) and CVC guidelines require additional security for unviable low bids but leave the exact mathematical multiplier to the procuring entity.
- **Adopted Formula**:
  $$\text{Shortfall Amount} = \max\left(0, (0.85 \times \text{Estimated Cost}) - \text{Evaluated Price}\right)$$
  $$\text{Shortfall \%} = \left(\frac{\text{Shortfall Amount}}{\text{Estimated Cost}}\right) \times 100$$
  $$\text{Additional Security Amount} = \text{quantize}\left(\frac{\text{Contract Value} \times \text{Shortfall \%}}{100}\right)$$
  Total Security required = Standard 5.00% + Shortfall %.

### Assumption 2: Comparison Denominator for Next-Ranked Bidder (10% Rule)
- **Context**: When an awarded contractor defaults on security within 21 days, guidelines permit offering the work to the next bidder if their price is "within 10%".
- **Adopted Rule**: The comparison threshold is calculated relative to the **original L1 evaluated price**:
  $$\text{Cut-off Price} = \text{L1 Price} \times 1.10$$
  If $\text{L2 Price} \le \text{Cut-off Price}$, the work is offered to L2 at L2's own quoted price. If L2 exceeds this limit, re-tender is mandatory.

### Assumption 3: Statutory Preference Interaction with QCBS
- **Context**: Indian Public Procurement Policy for MSEs and Make in India orders specify percentage margin bands relative to L1 (lowest price). Under QCBS, evaluation is based on composite scores (H1).
- **Adopted Policy**: For tenders evaluated under QCBS, the statutory price preference eligibility bands (MSE +15%, Class-I +20%) are computed relative to the **lowest commercial price among technically qualified bidders**. This policy is explicitly logged in the comparative statement.

### Assumption 4: Arithmetic Correction Precedence
- **Context**: Line-item discrepancies between quoted unit rates and quoted extended totals.
- **Adopted Rule**: **Unit rates govern over extended totals**. The extended total is re-computed as $\text{Quantity} \times \text{Quoted Unit Rate}$. The bidder is bound by this corrected price. Refusal to accept the correction results in disqualification and EMD forfeiture.

### Assumption 5: Calendar-Day Counting and Date Inclusivity
- **Context**: Calculation of 90-day bid validity and 45-day BG validity horizons.
- **Adopted Standard**: Date math is calendar-day based. Day 0 is the bid opening date; Day $N$ is $\text{Opening Date} + N\text{ days}$. An action executed on Day 90 is legally valid (inclusive). Bank Guarantees must remain valid through at least $\text{Opening Date} + 90 + 45\text{ days}$.

### Assumption 6: Single Responsive Bid Handling
- **Context**: Only one responsive bid survives technical qualification.
- **Adopted Policy**: If the tender configuration explicitly enables `single_bid_allowed = True`, award proceeds with recorded administrative justification. If disabled, a mandatory re-tender is triggered. Previous bidder and submission histories remain archived in SQLite.

### Assumption 7: Reserved Items Alongside Other Preferences
- **Context**: Products reserved exclusively for manufacture by Micro and Small Enterprises under the Public Procurement Policy for MSEs Order 2012.
- **Adopted Rule**: When `is_reserved_item = True`, **100% of the quantity** is allocated exclusively to the eligible MSE bidder matching the L1 price, completely superseding Class-I Make-in-India split rules.
