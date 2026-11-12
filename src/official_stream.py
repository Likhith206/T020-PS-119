"""
TENDERLENS — Official Evaluation Stream Processor
Prepared for Problem Statement PS-119 / Team T020 official evaluation dataset.

Processes the official command stream (commands.txt) against the official dataset:
- tenders.csv, tech_criteria.csv, bidders.csv, bidder_turnover.csv, similar_works.csv,
  blacklist.csv, bids.csv, evaluator_scores.csv, price_schedule.csv
Generates the exact four evaluation output CSV files:
- responsiveness.csv
- tech_scorecard.csv
- comparative_statement.csv
- award.csv
"""

import csv
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple


def d_round(val: Decimal, places: int = 2) -> Decimal:
    fmt = Decimal("10") ** -places
    return val.quantize(fmt, rounding=ROUND_HALF_UP)


def parse_date(d_str: str) -> Optional[date]:
    if not d_str or not d_str.strip():
        return None
    return datetime.strptime(d_str.strip(), "%Y-%m-%d").date()


class OfficialStreamRunner:
    def __init__(self, data_dir: str = "data/official", out_dir: str = "reports"):
        self.data_dir = Path(data_dir)
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.tenders: Dict[str, Dict[str, Any]] = {}
        self.tech_criteria: Dict[str, List[Dict[str, Any]]] = {}
        self.bidders: Dict[str, Dict[str, Any]] = {}
        self.turnover: Dict[str, List[Dict[str, Any]]] = {}
        self.similar_works: Dict[str, List[Dict[str, Any]]] = {}
        self.blacklist: Dict[str, List[Dict[str, Any]]] = {}
        self.bids: Dict[str, Dict[str, Any]] = {}
        self.evaluator_scores: Dict[Tuple[str, str], List[Decimal]] = {}  # (bid_id, crit_id) -> scores
        self.price_schedule: Dict[str, List[Dict[str, Any]]] = {}

        # Evaluation State per tender/bid
        self.responsiveness_results: Dict[str, Dict[str, Any]] = {}  # bid_id -> dict
        self.tech_scorecards: Dict[str, Dict[str, Any]] = {}  # bid_id -> dict
        self.financial_results: Dict[str, Dict[str, Any]] = {}  # bid_id -> dict
        self.award_records: List[Dict[str, Any]] = []

        # Tracking events
        self.loa_issued: Dict[str, Dict[str, Any]] = {}  # bid_id -> loa dict
        self.perf_security_received: Dict[str, Dict[str, Any]] = {}  # bid_id -> sec dict
        self.negotiated_prices: Dict[str, Decimal] = {}  # bid_id -> negotiated price
        self.preference_agreements: Dict[str, str] = {}  # bid_id -> type
        self.correction_responses: Dict[str, str] = {}  # bid_id -> ACCEPT / REFUSE
        self.extension_responses: Dict[str, str] = {}  # bid_id -> ACCEPT / REFUSE
        self.withdrawn_bids: set = set()

        self.load_data()

    def load_data(self):
        # 1. tenders.csv
        p_tenders = self.data_dir / "tenders.csv"
        with open(p_tenders, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                t_id = row["tender_id"].strip()
                self.tenders[t_id] = {
                    "tender_id": t_id,
                    "title": row["title"].strip(),
                    "evaluation_method": row["evaluation_method"].strip().upper(),
                    "category": row["category"].strip().upper(),
                    "estimated_cost": Decimal(row["estimated_cost"].strip()),
                    "quantity": int(row["quantity"].strip()),
                    "unit": row["unit"].strip(),
                    "tech_weight": Decimal(row["tech_weight"].strip()),
                    "fin_weight": Decimal(row["fin_weight"].strip()),
                    "mse_relax": row["mse_relax"].strip().lower() == "true",
                    "single_bid_allowed": row["single_bid_allowed"].strip().lower() == "true",
                    "item_reserved_for_mse": row["item_reserved_for_mse"].strip().lower() == "true",
                    "bid_opening_date": parse_date(row["bid_opening_date"]),
                    "bid_validity_days": int(row["bid_validity_days"].strip()),
                    "min_criterion_pct": Decimal(row["min_criterion_pct"].strip()),
                    "min_overall_pct": Decimal(row["min_overall_pct"].strip()),
                }

        # 2. tech_criteria.csv
        p_crit = self.data_dir / "tech_criteria.csv"
        with open(p_crit, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                t_id = row["tender_id"].strip()
                self.tech_criteria.setdefault(t_id, []).append({
                    "criterion_id": row["criterion_id"].strip(),
                    "criterion_name": row["criterion_name"].strip(),
                    "weight": Decimal(row["weight"].strip()),
                })

        # 3. bidders.csv
        p_bidders = self.data_dir / "bidders.csv"
        with open(p_bidders, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                b_id = row["bidder_id"].strip()
                self.bidders[b_id] = {
                    "bidder_id": b_id,
                    "bidder_name": row["bidder_name"].strip(),
                    "pan": row["pan"].strip(),
                    "gstin": row["gstin"].strip(),
                    "city": row["city"].strip(),
                    "is_mse": row["is_mse"].strip().lower() == "true",
                    "mse_certificate_valid_until": parse_date(row.get("mse_certificate_valid_until")),
                    "is_startup": row["is_startup"].strip().lower() == "true",
                    "startup_certificate_valid_until": parse_date(row.get("startup_certificate_valid_until")),
                }

        # 4. bidder_turnover.csv
        p_turnover = self.data_dir / "bidder_turnover.csv"
        with open(p_turnover, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                b_id = row["bidder_id"].strip()
                self.turnover.setdefault(b_id, []).append({
                    "financial_year": row["financial_year"].strip(),
                    "turnover": Decimal(row["turnover"].strip()),
                })

        # 5. similar_works.csv
        p_works = self.data_dir / "similar_works.csv"
        with open(p_works, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                b_id = row["bidder_id"].strip()
                self.similar_works.setdefault(b_id, []).append({
                    "work_id": row["work_id"].strip(),
                    "completion_date": parse_date(row["completion_date"]),
                    "work_value": Decimal(row["work_value"].strip()),
                    "client": row["client"].strip(),
                })

        # 6. blacklist.csv
        p_bl = self.data_dir / "blacklist.csv"
        with open(p_bl, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                b_id = row["bidder_id"].strip()
                self.blacklist.setdefault(b_id, []).append({
                    "blacklisted_from": parse_date(row["blacklisted_from"]),
                    "blacklisted_to": parse_date(row["blacklisted_to"]),
                    "order_ref": row["order_ref"].strip(),
                })

        # 7. bids.csv
        p_bids = self.data_dir / "bids.csv"
        with open(p_bids, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                bid_id = row["bid_id"].strip()
                self.bids[bid_id] = {
                    "bid_id": bid_id,
                    "tender_id": row["tender_id"].strip(),
                    "bidder_id": row["bidder_id"].strip(),
                    "submitted_ts": row["submitted_ts"].strip(),
                    "emd_mode": row["emd_mode"].strip().upper(),
                    "emd_amount": Decimal(row["emd_amount"].strip()),
                    "emd_bg_valid_until": parse_date(row.get("emd_bg_valid_until")),
                    "local_content_pct": Decimal(row["local_content_pct"].strip()),
                    "price_basis": row["price_basis"].strip().upper(),
                    "gst_rate_pct": Decimal(row["gst_rate_pct"].strip()),
                    "delivery_basis": row["delivery_basis"].strip().upper(),
                    "freight_amount": Decimal(row["freight_amount"].strip()),
                    "quoted_total": Decimal(row["quoted_total"].strip()),
                    "abnormal_price_justification": row["abnormal_price_justification"].strip().lower() == "true",
                    "status": "SUBMITTED",
                    "emd_action": "HELD",
                }

        # 8. evaluator_scores.csv
        p_scores = self.data_dir / "evaluator_scores.csv"
        with open(p_scores, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                bid_id = row["bid_id"].strip()
                c_id = row["criterion_id"].strip()
                score = Decimal(row["score"].strip())
                self.evaluator_scores.setdefault((bid_id, c_id), []).append(score)

        # 9. price_schedule.csv
        p_sched = self.data_dir / "price_schedule.csv"
        with open(p_sched, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                bid_id = row["bid_id"].strip()
                self.price_schedule.setdefault(bid_id, []).append({
                    "line_no": int(row["line_no"].strip()),
                    "item_code": row["item_code"].strip(),
                    "description": row["description"].strip(),
                    "quantity": int(row["quantity"].strip()),
                    "unit_rate": Decimal(row["unit_rate"].strip()),
                    "line_total": Decimal(row["line_total"].strip()),
                })

    def execute_command_stream(self, commands_path: Optional[str] = None):
        c_path = Path(commands_path) if commands_path else self.data_dir / "commands.txt"
        with open(c_path, "r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                cmd = parts[0]
                args = parts[1:]
                self._dispatch_command(cmd, args, line_no)

        # Generate the four output CSV files
        self._write_output_csvs()

    def _dispatch_command(self, cmd: str, args: List[str], line_no: int):
        if cmd == "OPEN_TECHNICAL":
            self.cmd_open_technical(tender_id=args[0], op_date=args[1])
        elif cmd == "PRINT_RESPONSIVENESS":
            pass  # Will be exported to responsiveness.csv
        elif cmd == "PRINT_TECH_SCORECARD":
            pass  # Will be exported to tech_scorecard.csv
        elif cmd == "OPEN_FINANCIAL":
            self.cmd_open_financial(tender_id=args[0], op_date=args[1])
        elif cmd == "CORRECTION_RESPONSE":
            self.cmd_correction_response(bid_id=args[0], res_date=args[1], response=args[2])
        elif cmd == "PREFERENCE_RESPONSE":
            self.cmd_preference_response(bid_id=args[0], res_date=args[1], pref_type=args[2], response=args[3])
        elif cmd == "WITHDRAW":
            self.cmd_withdraw(bid_id=args[0], w_date=args[1])
        elif cmd == "NEGOTIATE":
            self.cmd_negotiate(tender_id=args[0], bid_id=args[1], n_date=args[2], price=args[3])
        elif cmd == "EXTENSION_REQUEST":
            pass  # Extension requested by authority
        elif cmd == "EXTENSION_RESPONSE":
            self.cmd_extension_response(bid_id=args[0], res_date=args[1], response=args[2])
        elif cmd == "LOA":
            self.cmd_loa(tender_id=args[0], bid_id=args[1], loa_date=args[2], qty=args[3])
        elif cmd == "PERF_SECURITY":
            self.cmd_perf_security(bid_id=args[0], sec_date=args[1], amount=args[2])
        elif cmd == "TIMER_CHECK":
            self.cmd_timer_check(check_date=args[0])
        elif cmd == "PRINT_COMPARATIVE":
            pass  # Will be exported to comparative_statement.csv
        elif cmd == "PRINT_AWARD":
            pass  # Will be exported to award.csv
        else:
            print(f"Unknown command: {cmd}")

    def cmd_open_technical(self, tender_id: str, op_date: str):
        tender = self.tenders[tender_id]
        opening_date = tender["bid_opening_date"]
        est_cost = tender["estimated_cost"]
        validity_days = tender["bid_validity_days"]
        # Validity end date: day 1 is day after opening, so day 90 = opening + 90 days
        validity_end = opening_date + timedelta(days=validity_days)
        # Required BG horizon: validity_end + 45 days
        min_bg_validity = validity_end + timedelta(days=45)

        required_emd = min(est_cost * Decimal("0.02"), Decimal("5000000.00"))

        for bid_id, bid in self.bids.items():
            if bid["tender_id"] != tender_id:
                continue
            bidder = self.bidders[bid["bidder_id"]]
            b_id = bidder["bidder_id"]

            # 1. EMD check
            emd_mode = bid["emd_mode"]
            emd_amt = bid["emd_amount"]
            bg_valid = bid["emd_bg_valid_until"]

            emd_status = "FAIL"
            if emd_mode == "EXEMPT_MSE":
                if bidder["is_mse"] and bidder["mse_certificate_valid_until"] and bidder["mse_certificate_valid_until"] >= opening_date:
                    emd_status = "EXEMPT"
                else:
                    emd_status = "FAIL"
            elif emd_mode == "EXEMPT_STARTUP":
                if bidder["is_startup"] and (not bidder["startup_certificate_valid_until"] or bidder["startup_certificate_valid_until"] >= opening_date):
                    emd_status = "EXEMPT"
                else:
                    emd_status = "FAIL"
            elif emd_mode == "BANK_GUARANTEE":
                if emd_amt >= required_emd and bg_valid and bg_valid >= min_bg_validity:
                    emd_status = "PASS"
                else:
                    emd_status = "FAIL"
            elif emd_mode == "DD":
                if emd_amt >= required_emd:
                    emd_status = "PASS"
                else:
                    emd_status = "FAIL"

            if emd_status == "EXEMPT":
                bid["emd_action"] = "EXEMPT"

            # 2. Turnover check (30% boundary)
            t_records = self.turnover.get(b_id, [])
            turnover_check = "FAIL"
            if tender["mse_relax"] and bidder["is_mse"] and bidder["mse_certificate_valid_until"] and bidder["mse_certificate_valid_until"] >= opening_date:
                turnover_check = "EXEMPT"
            else:
                if t_records:
                    tot_t = sum(r["turnover"] for r in t_records)
                    avg_t = tot_t / Decimal(len(t_records))
                    if avg_t >= (est_cost * Decimal("0.30")):
                        turnover_check = "PASS"

            # 3. Experience check (7-year window = 7 * 365 days back from opening, 80%/50%/40%)
            seven_years_ago = opening_date - timedelta(days=7 * 365)
            w_records = self.similar_works.get(b_id, [])
            valid_works = [
                w["work_value"] for w in w_records
                if w["completion_date"] and w["completion_date"] >= seven_years_ago
            ]
            exp_check = "FAIL"
            if tender["mse_relax"] and bidder["is_mse"] and bidder["mse_certificate_valid_until"] and bidder["mse_certificate_valid_until"] >= opening_date:
                exp_check = "EXEMPT"
            else:
                thresh_80 = est_cost * Decimal("0.80")
                thresh_50 = est_cost * Decimal("0.50")
                thresh_40 = est_cost * Decimal("0.40")

                count_80 = sum(1 for val in valid_works if val >= thresh_80)
                count_50 = sum(1 for val in valid_works if val >= thresh_50)
                count_40 = sum(1 for val in valid_works if val >= thresh_40)

                if count_80 >= 1 or count_50 >= 2 or count_40 >= 3:
                    exp_check = "PASS"

            # 4. Blacklist check
            bl_records = self.blacklist.get(b_id, [])
            is_blacklisted = False
            for bl in bl_records:
                if bl["blacklisted_from"] <= opening_date <= bl["blacklisted_to"]:
                    is_blacklisted = True
                    break
            blacklist_check = "FAIL" if is_blacklisted else "PASS"

            # Responsiveness determination
            is_responsive = (
                (emd_status in ("PASS", "EXEMPT")) and
                (turnover_check in ("PASS", "EXEMPT")) and
                (exp_check in ("PASS", "EXEMPT")) and
                (blacklist_check == "PASS")
            )
            resp_status = "RESPONSIVE" if is_responsive else "NON_RESPONSIVE"
            bid["status"] = resp_status

            self.responsiveness_results[bid_id] = {
                "tender_id": tender_id,
                "bid_id": bid_id,
                "bidder_id": b_id,
                "emd_status": emd_status,
                "turnover_check": turnover_check,
                "experience_check": exp_check,
                "blacklist_check": blacklist_check,
                "status": resp_status,
            }

            # If responsive, calculate technical score
            if is_responsive:
                self._evaluate_technical_scores(tender_id, bid_id)
            else:
                bid["technical_status"] = "NOT_EVALUATED"

    def _evaluate_technical_scores(self, tender_id: str, bid_id: str):
        tender = self.tenders[tender_id]
        min_crit = tender["min_criterion_pct"]
        min_overall = tender["min_overall_pct"]
        criteria = self.tech_criteria.get(tender_id, [])

        overall_weighted = Decimal("0.00")
        all_passed = True
        scores_by_crit = []

        for crit in criteria:
            c_id = crit["criterion_id"]
            weight = crit["weight"]
            scores = self.evaluator_scores.get((bid_id, c_id), [])
            if scores:
                avg_score = d_round(sum(scores) / Decimal(len(scores)), 2)
            else:
                avg_score = Decimal("0.00")

            weighted = d_round((avg_score * weight) / Decimal("100.00"), 2)
            passed = avg_score >= min_crit
            if not passed:
                all_passed = False

            overall_weighted += weighted
            scores_by_crit.append({
                "criterion_id": c_id,
                "average_score": avg_score,
                "weighted_score": weighted,
                "passed": passed,
            })

        overall_weighted = d_round(overall_weighted, 2)
        overall_passed = all_passed and (overall_weighted >= min_overall)

        self.tech_scorecards[bid_id] = {
            "criteria": scores_by_crit,
            "overall_score": overall_weighted,
            "passed": overall_passed,
        }

        if not overall_passed:
            self.bids[bid_id]["status"] = "TECHNICALLY_DISQUALIFIED"

    def cmd_open_financial(self, tender_id: str, op_date: str):
        tender = self.tenders[tender_id]
        est_cost = tender["estimated_cost"]

        # Only evaluate technically qualified bids
        qualified_bids = [
            b_id for b_id, b in self.bids.items()
            if b["tender_id"] == tender_id and b["status"] == "RESPONSIVE" and self.tech_scorecards.get(b_id, {}).get("passed", False)
        ]

        if not qualified_bids:
            return

        # 1. Normalise price & arithmetic corrections
        bid_calc = {}
        for bid_id in qualified_bids:
            b = self.bids[bid_id]
            sched = self.price_schedule.get(bid_id, [])

            # Correct arithmetic: unit_rate * qty binds!
            corrected_total = sum(d_round(item["quantity"] * item["unit_rate"], 2) for item in sched)
            gst_added = Decimal("0.00")
            if b["price_basis"] == "GST_EXCLUSIVE":
                gst_added = d_round(corrected_total * (b["gst_rate_pct"] / Decimal("100.00")), 2)

            freight_added = Decimal("0.00")
            if b["delivery_basis"] == "EX_WORKS":
                freight_added = d_round(b["freight_amount"], 2)

            normalised_price = corrected_total + gst_added + freight_added
            bid_calc[bid_id] = {
                "quoted_total": b["quoted_total"],
                "corrected_total": corrected_total,
                "gst_added": gst_added,
                "freight_added": freight_added,
                "normalised_price": normalised_price,
            }

        # 2. Abnormally low bid analysis
        avg_price = sum(v["normalised_price"] for v in bid_calc.values()) / Decimal(len(bid_calc))
        thresh_85_est = est_cost * Decimal("0.85")
        thresh_80_avg = avg_price * Decimal("0.80")

        for bid_id, calc in bid_calc.items():
            norm_p = calc["normalised_price"]
            is_abnormal = (norm_p < thresh_85_est) or (norm_p < thresh_80_avg)
            calc["abnormally_low"] = is_abnormal

            # If abnormally low and justification is false, mark REJECTED!
            if is_abnormal and not self.bids[bid_id]["abnormal_price_justification"]:
                calc["rejected_abnormal"] = True
                self.bids[bid_id]["status"] = "REJECTED"
            else:
                calc["rejected_abnormal"] = False

        # 3. Ranking active bids
        active_bids = [b_id for b_id in qualified_bids if not bid_calc[b_id]["rejected_abnormal"]]

        if not active_bids:
            return

        lowest_norm = min(bid_calc[b_id]["normalised_price"] for b_id in active_bids)

        for bid_id in qualified_bids:
            calc = bid_calc[bid_id]
            tech_s = self.tech_scorecards[bid_id]["overall_score"]
            norm_p = calc["normalised_price"]

            if tender["evaluation_method"] == "QCBS":
                fin_s = d_round((lowest_norm / norm_p) * Decimal("100.00"), 2)
                tech_w = tender["tech_weight"] / Decimal("100.00")
                fin_w = tender["fin_weight"] / Decimal("100.00")
                final_s = d_round((tech_w * tech_s) + (fin_w * fin_s), 2)
            else:
                # LCS
                fin_s = d_round((lowest_norm / norm_p) * Decimal("100.00"), 2)
                final_s = Decimal("0.00")

            calc["tech_score"] = tech_s
            calc["fin_score"] = fin_s
            calc["final_score"] = final_s

        # Sort and assign ranks
        if tender["evaluation_method"] == "QCBS":
            active_bids.sort(key=lambda b: (-bid_calc[b]["final_score"], bid_calc[b]["normalised_price"]))
        else:
            active_bids.sort(key=lambda b: (bid_calc[b]["normalised_price"], -bid_calc[b]["tech_score"]))

        for r_idx, b_id in enumerate(active_bids, start=1):
            bid_calc[b_id]["rank"] = r_idx

        # If rejected, give empty or last rank
        for b_id in qualified_bids:
            if b_id not in bid_calc or "rank" not in bid_calc[b_id]:
                bid_calc[b_id]["rank"] = len(active_bids) + 1

            self.financial_results[b_id] = {
                "tender_id": tender_id,
                "bid_id": b_id,
                **bid_calc[b_id],
            }

    def cmd_correction_response(self, bid_id: str, res_date: str, response: str):
        self.correction_responses[bid_id] = response
        if response == "REFUSE":
            self.bids[bid_id]["status"] = "REJECTED"
            self.bids[bid_id]["emd_action"] = "FORFEITED"

    def cmd_preference_response(self, bid_id: str, res_date: str, pref_type: str, response: str):
        if response == "ACCEPT":
            self.preference_agreements[bid_id] = pref_type

    def cmd_withdraw(self, bid_id: str, w_date: str):
        self.withdrawn_bids.add(bid_id)
        self.bids[bid_id]["status"] = "WITHDRAWN"
        self.bids[bid_id]["emd_action"] = "FORFEITED"

    def cmd_negotiate(self, tender_id: str, bid_id: str, n_date: str, price: str):
        tender = self.tenders[tender_id]
        est_cost = tender["estimated_cost"]
        fin = self.financial_results.get(bid_id)
        if fin:
            p_val = fin["normalised_price"]
            # Negotiation only permitted if L1 exceeds estimated cost by >10%
            if p_val > (est_cost * Decimal("1.10")):
                self.negotiated_prices[bid_id] = Decimal(price)

    def cmd_extension_response(self, bid_id: str, res_date: str, response: str):
        self.extension_responses[bid_id] = response
        if response == "REFUSE":
            # Bidder exits cleanly without forfeiture
            self.bids[bid_id]["emd_action"] = "RETURNED"

    def cmd_loa(self, tender_id: str, bid_id: str, loa_date: str, qty: str):
        self.loa_issued[bid_id] = {
            "tender_id": tender_id,
            "bid_id": bid_id,
            "loa_date": parse_date(loa_date),
            "quantity": int(qty),
        }

    def cmd_perf_security(self, bid_id: str, sec_date: str, amount: str):
        self.perf_security_received[bid_id] = {
            "sec_date": parse_date(sec_date),
            "amount": Decimal(amount),
        }

    def cmd_timer_check(self, check_date: str):
        c_date = parse_date(check_date)
        # Check all LOAs issued: if > 21 days and no security furnished -> Default!
        for bid_id, loa in self.loa_issued.items():
            if bid_id in self.perf_security_received:
                continue
            loa_d = loa["loa_date"]
            if (c_date - loa_d).days > 21:
                # Defaulted!
                self.bids[bid_id]["status"] = "REJECTED"
                self.bids[bid_id]["emd_action"] = "FORFEITED"

    def _determine_final_awards(self):
        self.award_records.clear()

        # Group tenders
        for t_id, tender in self.tenders.items():
            t_bids = [b_id for b_id, b in self.bids.items() if b["tender_id"] == t_id]

            # Find all bids that received LOA and secured performance security
            for b_id in t_bids:
                if b_id in self.loa_issued and b_id in self.perf_security_received:
                    loa = self.loa_issued[b_id]
                    sec = self.perf_security_received[b_id]
                    fin = self.financial_results[b_id]

                    unit_p = d_round(fin["normalised_price"] / Decimal(tender["quantity"]), 2)
                    contract_val = d_round(unit_p * Decimal(loa["quantity"]), 2)

                    # Determine basis
                    pref = self.preference_agreements.get(b_id)
                    if b_id in self.negotiated_prices:
                        basis = "NEGOTIATED"
                        contract_val = self.negotiated_prices[b_id]
                        unit_p = d_round(contract_val / Decimal(loa["quantity"]), 2)
                    elif pref in ("MSE_MATCH", "LOCAL_MATCH"):
                        basis = pref
                        # Matches L1 unit price
                        l1_bid_id = next((b for b in t_bids if self.financial_results.get(b, {}).get("rank") == 1), None)
                        if l1_bid_id:
                            unit_p = d_round(self.financial_results[l1_bid_id]["normalised_price"] / Decimal(tender["quantity"]), 2)
                        contract_val = d_round(unit_p * Decimal(loa["quantity"]), 2)
                    elif fin.get("rank") == 1:
                        basis = "QCBS" if tender["evaluation_method"] == "QCBS" else "L1"
                    else:
                        basis = "NEXT_RANKED"

                    # Calculate performance security percentage
                    # Normal: 3%, or calculated from amount
                    sec_pct = d_round((sec["amount"] / contract_val) * Decimal("100.00"), 2)

                    self.award_records.append({
                        "tender_id": t_id,
                        "bid_id": b_id,
                        "basis": basis,
                        "quantity": loa["quantity"],
                        "unit_price": unit_p,
                        "contract_value": contract_val,
                        "performance_security_pct": sec_pct,
                        "emd_action": "RETURNED" if self.bids[b_id]["emd_action"] != "FORFEITED" else "FORFEITED",
                        "status": "AWARDED",
                    })

    def _write_output_csvs(self):
        self._determine_final_awards()

        # 1. responsiveness.csv
        p_resp = self.out_dir / "responsiveness.csv"
        with open(p_resp, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tender_id", "bid_id", "bidder_id", "emd_status", "turnover_check", "experience_check", "blacklist_check", "status"])
            for b_id in sorted(self.responsiveness_results.keys()):
                r = self.responsiveness_results[b_id]
                writer.writerow([
                    r["tender_id"], r["bid_id"], r["bidder_id"],
                    r["emd_status"], r["turnover_check"], r["experience_check"], r["blacklist_check"], r["status"]
                ])

        # 2. tech_scorecard.csv
        p_score = self.out_dir / "tech_scorecard.csv"
        with open(p_score, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tender_id", "bid_id", "criterion_id", "average_score", "weighted_score", "passed"])
            for b_id in sorted(self.tech_scorecards.keys()):
                sc = self.tech_scorecards[b_id]
                t_id = self.bids[b_id]["tender_id"]
                tot_weighted = Decimal("0.00")
                tot_avg = Decimal("0.00")
                for crit in sc["criteria"]:
                    writer.writerow([
                        t_id, b_id, crit["criterion_id"],
                        f"{crit['average_score']:.2f}",
                        f"{crit['weighted_score']:.2f}",
                        "true" if crit["passed"] else "false"
                    ])
                    tot_weighted += crit["weighted_score"]
                    tot_avg += crit["average_score"]

                # TOTAL row
                writer.writerow([
                    t_id, b_id, "TOTAL",
                    f"{tot_avg:.2f}",
                    f"{tot_weighted:.2f}",
                    "true" if sc["passed"] else "false"
                ])

        # 3. comparative_statement.csv
        p_comp = self.out_dir / "comparative_statement.csv"
        with open(p_comp, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "tender_id", "bid_id", "quoted_total", "corrected_total", "gst_added", "freight_added",
                "normalised_price", "abnormally_low", "tech_score", "fin_score", "final_score", "rank"
            ])
            # Order by tender_id and rank
            sorted_fin = sorted(self.financial_results.values(), key=lambda x: (x["tender_id"], x.get("rank", 999)))
            for fin in sorted_fin:
                writer.writerow([
                    fin["tender_id"],
                    fin["bid_id"],
                    f"{fin['quoted_total']:.2f}",
                    f"{fin['corrected_total']:.2f}",
                    f"{fin['gst_added']:.2f}",
                    f"{fin['freight_added']:.2f}",
                    f"{fin['normalised_price']:.2f}",
                    "true" if fin["abnormally_low"] else "false",
                    f"{fin['tech_score']:.2f}",
                    f"{fin['fin_score']:.2f}",
                    f"{fin['final_score']:.2f}" if self.tenders[fin["tender_id"]]["evaluation_method"] == "QCBS" else "-",
                    fin.get("rank", "-")
                ])

        # 4. award.csv
        p_award = self.out_dir / "award.csv"
        with open(p_award, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tender_id", "bid_id", "basis", "quantity", "unit_price", "contract_value", "performance_security_pct", "emd_action", "status"])
            for aw in self.award_records:
                writer.writerow([
                    aw["tender_id"],
                    aw["bid_id"],
                    aw["basis"],
                    aw["quantity"],
                    f"{aw['unit_price']:.2f}",
                    f"{aw['contract_value']:.2f}",
                    f"{aw['performance_security_pct']:.2f}",
                    aw["emd_action"],
                    aw["status"]
                ])
