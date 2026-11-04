"""
TENDERLENS — Eligibility Evaluation Engine (BR-01 / FR-03)
Evaluates bidder blacklisting, average annual turnover (30% boundary test),
similar work experience (80% / 50% / 40% rules), and MSE relaxation policy.
"""

import uuid
from decimal import Decimal
from typing import List, Tuple, Dict, Any, Optional
from src.models import Tender, Bidder, BidderExperience, BidderCertificate, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, format_inr
from src.utils.date_utils import parse_date, years_between, now_iso, is_on_or_before


class EligibilityEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("eligibility", {})
        self.min_turnover_pct = to_decimal(self.config.get("min_turnover_pct_of_estimate", "30.00"))
        self.experience_lookback_years = float(self.config.get("experience_lookback_years", 7))

    def evaluate(
        self,
        tender: Tender,
        bidder: Bidder,
        avg_turnover: Decimal,
        experiences: List[BidderExperience],
        certificates: List[BidderCertificate]
    ) -> Tuple[bool, str, List[DecisionRecord]]:
        """
        Evaluates complete eligibility.
        Returns: (is_eligible, reason_code, list_of_decisions)
        """
        decisions: List[DecisionRecord] = []
        est_cost = tender.estimated_cost
        required_turnover = quantize_money((est_cost * self.min_turnover_pct) / Decimal("100.00"))

        input_snapshot = {
            "bidder_id": bidder.bidder_id,
            "tender_id": tender.tender_id,
            "estimated_cost": str(est_cost),
            "average_turnover": str(avg_turnover),
            "is_blacklisted": bidder.is_blacklisted,
            "blacklisted_since": bidder.blacklisted_since,
            "mse_relax_enabled": tender.mse_relax_enabled,
            "experiences_count": len(experiences)
        }

        # 1. Blacklisting Check
        if bidder.is_blacklisted:
            # Check if blacklisted on or prior to bid opening date
            is_blacklisted_effective = True
            if bidder.blacklisted_since:
                is_blacklisted_effective = is_on_or_before(bidder.blacklisted_since, tender.bid_opening_date)

            if is_blacklisted_effective:
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bidder.bidder_id,
                    rule_id="BR-01",
                    evaluation_stage="ELIGIBILITY",
                    input_values=input_snapshot,
                    required_thresholds={"blacklisted_allowed": False},
                    calculation_details="Bidder is blacklisted as of bid opening date.",
                    result="FAIL",
                    human_explanation=f"Bidder is blacklisted since {bidder.blacklisted_since}. Reason: {bidder.blacklisting_reason or 'Order of competent authority'}.",
                    evidence_reference="Blacklist Registry Record",
                    created_at=now_iso()
                )
                decisions.append(dec)
                return False, "BLACKLISTED", decisions

        # 2. Check MSE Relaxation
        has_valid_mse = any(c.cert_type == "MSE" and c.is_valid for c in certificates)
        mse_relaxed = tender.mse_relax_enabled and has_valid_mse

        if mse_relaxed:
            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=bidder.bidder_id,
                rule_id="BR-01",
                evaluation_stage="ELIGIBILITY",
                input_values=input_snapshot,
                required_thresholds={"mse_relaxation": True},
                calculation_details="MSE Relaxation active and valid MSE certificate found.",
                result="PASS",
                human_explanation="Bidder qualifies via MSE exemption from prior turnover and experience criteria.",
                evidence_reference="Valid MSE Certificate",
                created_at=now_iso()
            )
            decisions.append(dec)
            return True, "QUALIFIED_MSE_RELAXED", decisions

        # 3. Turnover Evaluation
        # Mandatory boundary case: Exactly 30% turnover must PASS
        turnover_passed = avg_turnover >= required_turnover
        turnover_result = "PASS" if turnover_passed else "FAIL"
        turnover_expl = (
            f"Average annual turnover of {format_inr(avg_turnover)} satisfies minimum required {format_inr(required_turnover)} (30% of estimate)."
            if turnover_passed else
            f"Average annual turnover of {format_inr(avg_turnover)} is below required {format_inr(required_turnover)} (30% of estimate)."
        )
        dec_turnover = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bidder.bidder_id,
            rule_id="BR-01",
            evaluation_stage="ELIGIBILITY",
            input_values=input_snapshot,
            required_thresholds={"min_turnover_pct": "30.00", "min_turnover_amount": str(required_turnover)},
            calculation_details=f"Average turnover {format_inr(avg_turnover)} >= Required {format_inr(required_turnover)}: {turnover_passed}",
            result=turnover_result,
            human_explanation=turnover_expl,
            evidence_reference="Audited Financial Statements (Last 3 FY)",
            created_at=now_iso()
        )
        decisions.append(dec_turnover)

        if not turnover_passed:
            return False, "TURNOVER_INSUFFICIENT", decisions

        # 4. Past Experience Evaluation
        # Filter experiences within the last 7 years from bid opening date
        valid_exps = []
        for exp in experiences:
            diff_years = years_between(exp.completion_date, tender.bid_opening_date)
            if 0.0 <= diff_years <= self.experience_lookback_years:
                valid_exps.append(exp)

        exp_80 = quantize_money(est_cost * Decimal("0.80"))
        exp_50 = quantize_money(est_cost * Decimal("0.50"))
        exp_40 = quantize_money(est_cost * Decimal("0.40"))

        count_80 = sum(1 for e in valid_exps if e.contract_value >= exp_80)
        count_50 = sum(1 for e in valid_exps if e.contract_value >= exp_50)
        count_40 = sum(1 for e in valid_exps if e.contract_value >= exp_40)

        exp_satisfied = False
        exp_rule_met = ""

        if count_80 >= 1:
            exp_satisfied = True
            exp_rule_met = f"Satisfied 1 work >= 80% ({format_inr(exp_80)}): found {count_80}"
        elif count_50 >= 2:
            exp_satisfied = True
            exp_rule_met = f"Satisfied 2 works >= 50% each ({format_inr(exp_50)}): found {count_50}"
        elif count_40 >= 3:
            exp_satisfied = True
            exp_rule_met = f"Satisfied 3 works >= 40% each ({format_inr(exp_40)}): found {count_40}"

        exp_result = "PASS" if exp_satisfied else "FAIL"
        exp_expl = (
            f"Similar work experience requirement satisfied: {exp_rule_met}."
            if exp_satisfied else
            f"Similar work experience not met. Requires: 1 work >= {format_inr(exp_80)}, OR 2 >= {format_inr(exp_50)}, OR 3 >= {format_inr(exp_40)} in last 7 years."
        )

        dec_exp = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bidder.bidder_id,
            rule_id="BR-01",
            evaluation_stage="ELIGIBILITY",
            input_values={"valid_experiences_in_7_yrs": len(valid_exps), "count_80": count_80, "count_50": count_50, "count_40": count_40},
            required_thresholds={"option_1": f"1 >= {exp_80}", "option_2": f"2 >= {exp_50}", "option_3": f"3 >= {exp_40}"},
            calculation_details=f"80% works: {count_80}, 50% works: {count_50}, 40% works: {count_40}",
            result=exp_result,
            human_explanation=exp_expl,
            evidence_reference="Completion Certificates",
            created_at=now_iso()
        )
        decisions.append(dec_exp)

        if not exp_satisfied:
            return False, "EXPERIENCE_INSUFFICIENT", decisions

        return True, "QUALIFIED", decisions
