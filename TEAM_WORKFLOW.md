# TENDERLENS — Unified Team Workflow & Collaboration Standards

---

## 1. Unified Product Ownership Principle
In strict adherence to project specifications:
- **TENDERLENS is built as ONE unified, integrated application.**
- There are no fragmented codebases, parallel versions, or isolated student silos.
- Both team members share end-to-end understanding and defense capability across every architectural subsystem:
  1. Relational schema and Decimal numerical precision.
  2. Public procurement statutory rules (BR-01 through BR-12).
  3. Procurement Decision Graph (DAG) state machine and blockage logic.
  4. Cryptographic SHA-256 audit chaining and verification.
  5. What-if contingency simulation and RAM-isolated clones.

---

## 2. Engineering Standards & Quality Checklist
1. **Zero Float Rule**: Never use binary floating-point numbers for currency, prices, scores, or percentages. Always import `decimal.Decimal` and apply `quantize_money()` or `quantize_percent()`.
2. **Strict Two-Envelope Guard**: Never access, read, or print price schedules of a bidder whose technical status is not `QUALIFIED` and responsiveness status is not `RESPONSIVE`.
3. **Database Transactions**: All mutations must run inside `with db.transaction() as cur:` to guarantee atomicity and rollback on error.
4. **Parameterized SQL Only**: Never concatenate strings into SQL queries. Always pass tuples as query parameters to prevent SQL injection.
5. **No Silent Failures**: When configuration or CSV input fails validation, raise explicit `ValidationError` instances with actionable diagnostics.
6. **Automated Testing**: Any bug fix or new feature must be accompanied by an automated pytest test in `tests/`.

---

## 3. Git Workflow & Repository Hygiene
- Working branch: `feature/database-foundation` / `develop` / `main`.
- Untracked artifacts (`.venv`, `__pycache__`, `.pytest_cache`, `database/*.db`, `reports/*.json`) are maintained in `.gitignore`.
- No destructive git operations (`reset --hard`, deleting upstream branches) are permitted.
