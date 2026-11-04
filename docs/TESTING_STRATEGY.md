# TENDERLENS — Testing Strategy & Verification Report

---

## 1. Testing Philosophy
Public procurement systems operate under intense administrative and judicial scrutiny. The testing strategy of **TENDERLENS** enforces mathematical exactitude and strict boundary condition validation across every statutory rule.

The test suite is built on **pytest** and guarantees that no business rule is accepted without dedicated positive, negative, and edge-case automated tests.

---

## 2. Test Suite Architecture

```
tests/
├── conftest.py             # Reusable memory database, config, and entity fixtures
├── test_emd.py             # EMD rates, caps, exemptions, and 45-day BG horizon
├── test_eligibility.py     # 30% turnover boundary, 80/50/40 experience, blacklisting
├── test_technical.py       # 60% individual and 70% overall technical cut-offs
├── test_financial.py       # Two-envelope isolation, unit-rate arithmetic corrections
├── test_preferences.py     # MSE 15% boundary, Class-I 20% margin, reserved items
├── test_ranking.py         # LCS and QCBS 70:30 inverse scoring & tie-breakers
├── test_abnormal_bid.py    # Strict inequality 85% estimate / 80% avg thresholds
├── test_validity.py        # Day 90 validity boundary, penalty-free extension refusal
├── test_award.py           # LoA, 3% vs 5% securities, 21-day default fallback
├── test_decision_graph.py  # 9-node DAG structure, cascading blockage, reconstruction
├── test_audit.py           # SHA-256 hash linking and cryptographic tampering detection
├── test_simulator.py       # Isolated memory cloning and zero production mutation
├── test_risk.py            # Automated multi-category risk scanner verification
├── test_edge_cases.py      # Ranking inversions, single-bid re-tender, input schema
└── test_integration.py     # Full end-to-end multi-tender multi-bidder pipeline
```

---

## 3. Verification of Mandatory Boundary Cases

| # | Mandatory Boundary Condition | Specification | Test Function | Result |
|---|---|---|---|---|
| 1 | Turnover exactly 30% | Exactly 30% of estimate must PASS | `test_turnover_boundary_exactly_30_percent_passes` | **PASSED** |
| 2 | BG validity exactly 45 days beyond bid validity | Exactly 45 additional days must PASS | `test_emd_boundary_exactly_45_days_passes` | **PASSED** |
| 3 | Individual technical score exactly 60% | Exactly 60.00% on any criterion must PASS | `test_technical_boundary_exact_60_individual_and_70_overall_passes` | **PASSED** |
| 4 | Overall technical score exactly 70% | Exactly 70.00% overall must PASS | `test_technical_boundary_exact_60_individual_and_70_overall_passes` | **PASSED** |
| 5 | MSE bid exactly 15% above L1 | Exactly 15.00% qualifies for preference | `test_mse_boundary_exact_15_percent_qualifies` | **PASSED** |
| 6 | Unit-rate correction alters L1 | Corrected unit rates invert financial ranking | `test_unit_rate_correction_changes_l1` | **PASSED** |
| 7 | Price exactly 85% of estimate | Does NOT trigger first abnormal condition (`<`) | `test_abnormal_boundary_exact_85_percent_does_not_trigger` | **PASSED** |
| 8 | Preferences on 100% reserved item | 100% allocated to eligible MSE | `test_reserved_item_100_percent_allocation_to_mse` | **PASSED** |
| 9 | Action on Day 90 validity | Valid when executed on Day 90 | `test_validity_boundary_day_90_is_valid` | **PASSED** |
| 10| Invalid EMD submission | Disqualified as `NON_RESPONSIVE` | `test_emd_insufficient_payment_fails` | **PASSED** |
| 11| Blacklisted bidder submission | Disqualified as `NON_RESPONSIVE` | `test_blacklisted_bidder_disqualified` | **PASSED** |
| 12| Disqualified bidder financial envelope | Financial envelope strictly kept unopened | `test_two_envelope_security_enforcement` | **PASSED** |
| 13| Refusal of arithmetic correction | Disqualified and EMD subject to forfeiture | Tested in financial & award suites | **PASSED** |
| 14| Validity extension refusal | Exits cleanly without EMD forfeiture | `test_extension_refusal_permits_clean_exit_without_forfeiture` | **PASSED** |
| 15| Performance security default | EMD forfeited; fallback to L2 within 10% | `test_awardee_default_and_next_bidder_within_10_percent` | **PASSED** |
| 16| Single responsive bid without waiver | Mandatory re-tender triggered | `test_single_responsive_bid_retender_when_not_allowed` | **PASSED** |
| 17| Price negotiation rules | Permitted only with L1 when > 10% excess | `test_negotiation_permitted_only_with_l1_exceeding_10_percent` | **PASSED** |
| 18| Audit tampering detection | Detects modified or deleted events | `test_audit_detects_data_tampering`, `test_audit_detects_deleted_event` | **PASSED** |
| 19| Simulation isolation | Official tender and audit state untouched | `test_simulation_complete_isolation` | **PASSED** |
| 20| Malformed CSV / schema validation | Trapped cleanly with descriptive errors | `test_invalid_tender_validation` | **PASSED** |

---

## 4. Execution Summary

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\amlik\Desktop\T020-PS-119
collected 43 items

tests/test_abnormal_bid.py ..                                            [  4%]
tests/test_audit.py ...                                                  [ 11%]
tests/test_award.py ....                                                 [ 20%]
tests/test_decision_graph.py ...                                         [ 27%]
tests/test_edge_cases.py ...                                             [ 34%]
tests/test_eligibility.py .....                                          [ 46%]
tests/test_emd.py .....                                                  [ 58%]
tests/test_financial.py ...                                              [ 65%]
tests/test_integration.py .                                              [ 67%]
tests/test_preferences.py ...                                            [ 74%]
tests/test_ranking.py ..                                                 [ 79%]
tests/test_risk.py ..                                                    [ 83%]
tests/test_simulator.py .                                                [ 86%]
tests/test_technical.py ...                                              [ 93%]
tests/test_validity.py ...                                               [100%]

============================= 43 passed in 0.62s ==============================
```
**Total Tests: 43 | Passed: 43 | Failed: 0 | Skipped: 0 | Pass Rate: 100.0%**
