# PS-119 – Tender Bid Evaluation Engine with Technical Scoring, EMD, Bid Validity and Price Preference — Sample Data Pack

Prepared by 10 SECONDS for Team T020.

## Files

| File | What it holds | Row count |
|---|---|---|
| `tenders.csv` | 4 tenders (1 QCBS, 3 LCS) with estimate, quantity, flags and opening date | 4 data rows |
| `tech_criteria.csv` | Weighted technical criteria per tender | 16 data rows |
| `bidders.csv` | Bidders with MSE / startup status and certificate validity | 30 data rows |
| `bidder_turnover.csv` | Annual turnover for the last 3 financial years | 90 data rows |
| `similar_works.csv` | Similar completed works per bidder | 32 data rows |
| `blacklist.csv` | Blacklisting orders with period | 2 data rows |
| `bids.csv` | 30 bids with EMD, price basis, delivery basis, local content and quoted total | 30 data rows |
| `evaluator_scores.csv` | Scores 0-100 by 3 evaluators per criterion per bid | 360 data rows |
| `price_schedule.csv` | Price schedule lines (5 deliberate arithmetic errors) | 58 data rows |
| `commands.txt` | ~40 opening/correction/preference/extension/negotiation/LoA/security events and print requests | 56 command lines (excluding comments) |

Row numbers quoted below are 1-based data-row numbers (the header is row 0). Line numbers for `commands.txt` are physical line numbers including comment lines.

## Column reference

Conventions: dates `YYYY-MM-DD`; timestamps `YYYY-MM-DD HH:MM:SS` (24h, IST, no timezone suffix); money in Rs as plain decimals with 2 places (no commas, no symbol); percentages as plain numbers (12.5 means 12.5%); booleans `true`/`false`; IDs uppercase with a fixed prefix. An empty cell means "not applicable" and is only allowed where the notes say so.

### `tenders.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| tender_id | string | TND-nn | — | — |
| title | string | — | — | — |
| evaluation_method | enum | — | QCBS, LCS | — |
| category | enum | — | CONSULTANCY, GOODS, WORKS | similar-work category |
| estimated_cost | decimal | Rs | — | — |
| quantity | int | — | — | for preference quantity splits |
| unit | string | — | NOS, LOT | — |
| tech_weight | decimal | % | — | QCBS only |
| fin_weight | decimal | % | — | — |
| mse_relax | bool | — | — | — |
| single_bid_allowed | bool | — | — | — |
| item_reserved_for_mse | bool | — | — | — |
| bid_opening_date | date | — | — | technical opening; validity counted from here |
| bid_validity_days | int | days | 90 | — |
| min_criterion_pct | decimal | % | — | — |
| min_overall_pct | decimal | % | — | — |

### `tech_criteria.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| tender_id | string | — | tenders.csv | — |
| criterion_id | string | Cn | — | — |
| criterion_name | string | — | — | — |
| weight | decimal | — | sums to 100 | — |

### `bidders.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bidder_id | string | BDR-nnn | — | — |
| bidder_name | string | — | — | — |
| pan | string | AAAAA9999A | — | — |
| gstin | string | 15 chars | — | — |
| city | string | — | — | — |
| is_mse | bool | — | — | — |
| mse_certificate_valid_until | date | — | — | empty if not MSE |
| is_startup | bool | — | — | — |
| startup_certificate_valid_until | date | — | — | empty if not startup |

### `bidder_turnover.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bidder_id | string | — | bidders.csv | — |
| financial_year | string | YYYY-YY | — | last 3 FYs |
| turnover | decimal | Rs | — | — |

### `similar_works.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bidder_id | string | — | bidders.csv | — |
| work_id | string | WRK-nnnn | — | — |
| completion_date | date | — | — | 7-year window back from bid opening |
| work_value | decimal | Rs | — | compare with 80/50/40% of estimate |
| client | string | — | — | — |

### `blacklist.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bidder_id | string | — | bidders.csv | — |
| blacklisted_from | date | — | — | inclusive |
| blacklisted_to | date | — | — | inclusive |
| order_ref | string | — | — | — |

### `bids.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bid_id | string | BID-nnn | — | — |
| tender_id | string | — | tenders.csv | — |
| bidder_id | string | — | bidders.csv | — |
| submitted_ts | timestamp | — | — | — |
| emd_mode | enum | — | BANK_GUARANTEE, DD, EXEMPT_MSE, EXEMPT_STARTUP | — |
| emd_amount | decimal | Rs | — | required = 2% of estimate, max Rs 5000000 |
| emd_bg_valid_until | date | — | — | BANK_GUARANTEE only |
| local_content_pct | decimal | % | — | >= 50 = Class-I local supplier |
| price_basis | enum | — | GST_INCLUSIVE, GST_EXCLUSIVE | — |
| gst_rate_pct | decimal | % | — | rate to add when exclusive |
| delivery_basis | enum | — | FOR_DESTINATION, EX_WORKS | — |
| freight_amount | decimal | Rs | — | added when EX_WORKS |
| quoted_total | decimal | Rs | — | as written by the bidder (sum of line_total) |
| abnormal_price_justification | bool | — | — | — |

### `evaluator_scores.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bid_id | string | — | bids.csv | — |
| criterion_id | string | — | tech_criteria.csv | — |
| evaluator_id | string | EVL-n | — | — |
| score | decimal | 0-100 | — | average the 3 evaluators |

### `price_schedule.csv`

| Column | Type | Units / format | Allowed values | Notes |
|---|---|---|---|---|
| bid_id | string | — | bids.csv | — |
| line_no | int | — | — | — |
| item_code | string | — | — | — |
| description | string | — | — | — |
| quantity | int | — | — | — |
| unit_rate | decimal | Rs | — | binding |
| line_total | decimal | Rs | — | as written; may contain an arithmetic error |

## Command file format

`commands.txt` holds one command per line in the form `COMMAND_NAME|arg1|arg2|...`. Commands must be processed strictly in file order. Lines starting with `#` are comments and blank lines are ignored. An argument written as `-` means "not applicable". Every command used in this pack:

| Command | Arguments (in order) | Meaning |
|---|---|---|
| `OPEN_TECHNICAL` | `tender_id|date` | Open technical envelopes: timeline, EMD, eligibility, technical scoring |
| `OPEN_FINANCIAL` | `tender_id|date` | Open price envelopes of technically qualified bids; normalise and correct |
| `CORRECTION_RESPONSE` | `bid_id|date|ACCEPT or REFUSE` | Bidder's response to the arithmetic correction |
| `PREFERENCE_RESPONSE` | `bid_id|date|MSE_MATCH or LOCAL_MATCH|ACCEPT or DECLINE` | Offer to match L1 |
| `WITHDRAW` | `bid_id|date` | — |
| `NEGOTIATE` | `tender_id|bid_id|date|negotiated_price` | — |
| `EXTENSION_REQUEST` | `tender_id|date|days` | Authority seeks one validity extension |
| `EXTENSION_RESPONSE` | `bid_id|date|ACCEPT or REFUSE` | — |
| `LOA` | `tender_id|bid_id|date|quantity` | Letter of acceptance |
| `PERF_SECURITY` | `bid_id|date|amount` | Performance security furnished |
| `TIMER_CHECK` | `date` | Apply all deadlines (security 21 days, validity) up to this date |
| `PRINT_RESPONSIVENESS` | `tender_id` | — |
| `PRINT_TECH_SCORECARD` | `tender_id` | — |
| `PRINT_COMPARATIVE` | `tender_id` | — |
| `PRINT_AWARD` | `tender_id` | — |

## Planted scenarios

Every edge case in the brief, mapped to the exact record where it occurs, followed by extra traps.

- **EC-01 Turnover at exactly 30% of estimated cost**
  - BDR-015 (bid BID-022, TND-03, estimated cost Rs 10000000.00): turnover 2700000 / 3000000 / 3300000 -> average Rs 3000000.00 = exactly 30% — eligible; experience: 2 works of exactly 50% (Rs 5000000.00 each) — `bidder_turnover.csv row 43; similar_works.csv row 16`
- **EC-02 EMD bank guarantee validity ending exactly 45 days after bid validity**
  - BID-030 (TND-01): opened 2026-06-16, bid validity ends 2026-09-14; EMD bank guarantee valid until 2026-10-29 = exactly 45 days beyond — valid; BID-002's BG ends one day earlier (44 days) — NON_RESPONSIVE — `bids.csv row 30, bids.csv row 2`
- **EC-03 Criterion score exactly 60% and overall exactly 70%**
  - BID-018 (TND-01): C1 (weight 30) averages exactly 60.00; weighted overall = 18 + 19 + 18 + 15 = exactly 70.00 — qualifies on both floors — `evaluator_scores.csv row 205 (12 rows)`
- **EC-04 MSE quote at exactly 15% above L1**
  - TND-03: L1 is BID-022 at Rs 8500000.00; MSE bidder BID-020 quotes Rs 9775000.00 = exactly 15% above L1 — within the band, may match L1 for 25% of quantity (125 laptops); accepts on 2026-08-10 — `bids.csv row 20; commands.txt line 22`
- **EC-05 Unit-rate correction changing the L1 ranking**
  - TND-03: BID-008 quotes Rs 8400000.00 (apparently L1) but 500 x 17600.00 = Rs 8800000.00; the corrected total binds and BID-022 (Rs 8500000.00) becomes L1; the bidder accepts the correction — `price_schedule.csv row 14; commands.txt line 21`
- **EC-06 Bid price exactly 85% of estimated cost**
  - TND-03: BID-022 at Rs 8500000.00 = exactly 85% of the Rs 10000000.00 estimate — NOT below 85%, and above 80% of the qualified average, so not abnormally low; BID-025 at Rs 7800000.00 has no justification flag — rejected as abnormally low — `bids.csv row 22, bids.csv row 25`
- **EC-07 Both MSE and local-content preferences on a reserved item**
  - TND-02 (item reserved for MSE): L1 BID-006 Rs 1920000.00 (non-MSE); MSE BID-023 at Rs 2100000.00 (9.4% above) matches L1 and, the item being reserved, takes 100% of the 2000 chairs; local supplier BID-027 (62% local content, 13.5% above L1) also accepts LOCAL_MATCH but its share comes from the remainder = 0 — `commands.txt lines 13, 14, 18, 31`
- **EC-08 LoA issued on day 90 of validity**
  - TND-03 opened 2026-07-07; LoAs issued on 2026-10-05 = day 90 of bid validity (no extension sought) — still valid — `commands.txt lines 42, 43, 44`
- **Extra traps (not in the brief, but realistic):**
  - BID-019 (TND-01): C2 averages 58.00 (< 60) — TECHNICALLY_DISQUALIFIED even though its overall is above 70; BID-021: every criterion >= 60 but overall 69.30 — disqualified; price envelopes stay unopened — `evaluator_scores.csv row 217, evaluator_scores.csv row 241`
  - Arithmetic errors (5): BID-008 (ec5), BID-014 line 1 under-totalled, BID-028 line over-totalled, BID-016 BOQ-02 (bidder REFUSES the correction — bid rejected, EMD forfeited), BID-013 BOQ-02 (correction LOWERS the total) — `price_schedule.csv; refusal commands.txt line 28`
  - TND-02 normalisation: BID-011 quotes 900.00 GST-exclusive -> 1062.00 per chair after 18% GST; BID-010 quotes 940.00 ex-works + Rs 60000.00 freight = Rs 1940000.00 — looks cheapest before normalisation, is not L1 after — `bids.csv row 11, bids.csv row 10`
  - BID-007: MSE certificate expired 2026-05-31 (before opening) — EMD exemption invalid, no EMD paid -> NON_RESPONSIVE — `bids.csv row 7`
  - BID-009: bidder blacklisted from 2026-05-28 (before TND-03 opening) — NON_RESPONSIVE; BDR-006 is blacklisted only from the day AFTER TND-01 opened — still responsive there — `blacklist.csv row 2, blacklist.csv row 1`
  - BID-029: its only 80%+ work was completed 7 years + 2 days before opening — outside the 7-year window, other work too small -> NON_RESPONSIVE (experience) — `similar_works.csv row 2`
  - TND-04 has MSE_RELAX: MSE BID-017 (turnover ~Rs 21 lakh against an Rs 72 lakh threshold, one small work) is exempt and stays responsive; startup BID-001 is EMD-exempt — `bids.csv row 17`
  - TND-04: L1 BID-015 at Rs 26460000.00 is more than 10% above the estimate — NEGOTIATE allowed, negotiated price lower, no re-ranking; NEGOTIATE on TND-03 (BID-022, 15% BELOW estimate) is not permitted — `commands.txt lines 27, 30, 32, 39`
  - BID-012 WITHDRAWS on 2026-08-12 during bid validity — EMD forfeited — `commands.txt line 26`
  - TND-01: validity extended by 30 days (one bidder BID-018 refuses and exits without forfeiture); winner BID-003 gets LoA 2026-09-08 but furnishes no performance security within 21 days — EMD forfeited at the 2026-09-30 timer check; next-ranked BID-014 is offered at its own price (within 10% of L1) and secures on 2026-10-12 — `commands.txt lines 33, 34, 35, 36, 37, 38, 40, 41, 45`

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.

## Output format expected at evaluation

Produce these CSV files (header row, same conventions as above, rows sorted as stated). Where the brief is silent on a format detail the choice below is binding for evaluation.

### `responsiveness.csv`

One row per bid.

Columns, in order: `tender_id`, `bid_id`, `bidder_id`, `emd_status`, `turnover_check`, `experience_check`, `blacklist_check`, `status`

### `tech_scorecard.csv`

One row per bid per criterion plus a TOTAL row per bid.

Columns, in order: `tender_id`, `bid_id`, `criterion_id`, `average_score`, `weighted_score`, `passed`

### `comparative_statement.csv`

One row per opened bid, ordered by rank.

Columns, in order: `tender_id`, `bid_id`, `quoted_total`, `corrected_total`, `gst_added`, `freight_added`, `normalised_price`, `abnormally_low`, `tech_score`, `fin_score`, `final_score`, `rank`

### `award.csv`

One row per award/preference allocation or decision per tender.

Columns, in order: `tender_id`, `bid_id`, `basis`, `quantity`, `unit_price`, `contract_value`, `performance_security_pct`, `emd_action`, `status`

Binding choices: bid validity day 1 is the day after bid_opening_date, so day 90 = opening + 90 days; the BG must be valid until at least validity end + 45 days. Normalised price = corrected total (sum of quantity x unit_rate) + GST (if exclusive) + freight (if ex-works). Scores to 2 decimals. `status` RESPONSIVE, NON_RESPONSIVE, TECHNICALLY_DISQUALIFIED, REJECTED, WITHDRAWN, AWARDED, RE_TENDERED; `basis` L1, QCBS, MSE_MATCH, LOCAL_MATCH, NEXT_RANKED, NEGOTIATED; `emd_action` RETURNED, FORFEITED, EXEMPT, HELD.
