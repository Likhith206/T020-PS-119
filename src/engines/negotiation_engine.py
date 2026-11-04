"""
TENDERLENS — Negotiation Protocol Engine (BR-11 / FR-13)
Restricts negotiation strictly to L1 bidder when price exceeds estimated cost by >10%.
Ensures negotiated price never exceeds original L1 and preserves rankings and price history.
"""

import uuid
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional
from src.models import Tender, Bid, FinancialEvaluation, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, format_inr
from src.utils.date_utils import now_iso


class NegotiationEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("negotiation", {})
        self.trigger_excess_pct = to_decimal(self.config.get("excess_estimate_trigger_pct", "10.00"))
        self.l1_only = self.config.get("allow_negotiation_only_with_l1", True)

    def evaluate_negotiation_eligibility(
        self,
        tender: Tender,
        bid: Bid,
        evaluation: FinancialEvaluation,
        is_l1: bool
    ) -> Tuple[bool, str, Decimal, DecisionRecord]:
        """
        Determines if price negotiation is legally permitted.
        Returns: (is_permitted, reason_code, max_permitted_price, decision_record)
        """
        price = evaluation.final_comparative_price
        est_cost = tender.estimated_cost
        excess_threshold = quantize_money(est_cost * (Decimal("1.00") + (self.trigger_excess_pct / Decimal("100.00"))))

        input_snapshot = {
            "tender_id": tender.tender_id,
            "bidder_id": bid.bidder_id,
            "quoted_price": str(price),
            "estimated_cost": str(est_cost),
            "is_l1": is_l1
        }
        required_thresholds = {
            "trigger_excess_pct": str(self.trigger_excess_pct),
            "excess_cutoff_price": str(excess_threshold),
            "negotiate_with_l1_only": self.l1_only
        }

        if not is_l1 and self.l1_only:
            expl = f"Post-tender negotiation with non-L1 bidder {bid.bidder_id} is strictly prohibited under CVC guidelines."
            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=bid.bidder_id,
                rule_id="BR-11",
                evaluation_stage="NEGOTIATION",
                input_values=input_snapshot,
                required_thresholds=required_thresholds,
                calculation_details="Bidder is not L1. Non-L1 negotiations disallowed.",
                result="FAIL",
                human_explanation=expl,
                evidence_reference="Central Vigilance Commission (CVC) Procurement Guidelines",
                created_at=now_iso()
            )
            return False, "NON_L1_NEGOTIATION_PROHIBITED", price, dec

        is_exorbitant = price > excess_threshold
        if is_exorbitant:
            expl = (
                f"L1 price {format_inr(price)} exceeds estimated cost {format_inr(est_cost)} by more than 10% "
                f"(Threshold: {format_inr(excess_threshold)}). Price negotiation with L1 is justified and permitted."
            )
            res = "PASS"
            action = "NEGOTIATION_RECOMMENDED"
        else:
            expl = (
                f"L1 price {format_inr(price)} does not exceed estimated cost by >10% (Threshold: {format_inr(excess_threshold)}). "
                "Routine negotiation is discouraged to preserve tender sanctity."
            )
            res = "SKIPPED"
            action = "NEGOTIATION_NOT_REQUIRED"

        dec = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bid.bidder_id,
            rule_id="BR-11",
            evaluation_stage="NEGOTIATION",
            input_values=input_snapshot,
            required_thresholds=required_thresholds,
            calculation_details=f"Price {format_inr(price)} > 110% of Estimate ({format_inr(excess_threshold)}): {is_exorbitant}",
            result=res,
            human_explanation=expl,
            evidence_reference="Price Reasonableness Assessment",
            created_at=now_iso()
        )

        return is_exorbitant, action, price, dec
