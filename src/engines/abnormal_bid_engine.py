"""
TENDERLENS — Abnormally Low Bid Analysis Engine (BR-07 / FR-09)
Detects abnormally low prices using strict dual-threshold comparisons:
1. Price < 85% of estimated cost (Strict inequality: Exactly 85% does NOT trigger)
2. Price < 80% of average qualified bid price
Enforces rate analysis/capacity justification and calculates additional performance security.
"""

import uuid
from decimal import Decimal
from typing import List, Tuple, Dict, Any, Optional
from src.models import Tender, Bid, FinancialEvaluation, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, quantize_percent, format_inr
from src.utils.date_utils import now_iso


class AbnormalBidEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("abnormal_bid", {})
        self.est_threshold_pct = to_decimal(self.config.get("estimate_shortfall_threshold_pct", "85.00"))
        self.avg_threshold_pct = to_decimal(self.config.get("average_bid_shortfall_threshold_pct", "80.00"))
        self.abnormal_base_sec_pct = to_decimal(self.config.get("abnormal_base_security_pct", "5.00"))

    def analyze_bid(
        self,
        tender: Tender,
        bid: Bid,
        evaluation: FinancialEvaluation,
        all_qualified_evals: List[FinancialEvaluation],
        justification_status: Optional[str] = "ACCEPTED"
    ) -> Tuple[bool, bool, Decimal, DecisionRecord]:
        """
        Analyzes whether a bid is abnormally low and determines acceptance/additional security.
        Returns: (is_abnormal, is_accepted, additional_security_amount, decision_record)
        """
        price = evaluation.final_comparative_price
        est_cost = tender.estimated_cost

        # 85% of estimated cost
        threshold_estimate = quantize_money((est_cost * self.est_threshold_pct) / Decimal("100.00"))

        # Average of all qualified bids
        valid_prices = [e.final_comparative_price for e in all_qualified_evals]
        avg_price = quantize_money(sum(valid_prices) / Decimal(len(valid_prices))) if valid_prices else price
        threshold_average = quantize_money((avg_price * self.avg_threshold_pct) / Decimal("100.00"))

        # Strict less-than comparisons (boundary case: exactly 85% does NOT trigger)
        triggers_est_shortfall = price < threshold_estimate
        triggers_avg_shortfall = price < threshold_average
        is_abnormal = triggers_est_shortfall or triggers_avg_shortfall

        input_snapshot = {
            "bid_id": bid.bid_id,
            "bidder_id": bid.bidder_id,
            "final_comparative_price": str(price),
            "estimated_cost": str(est_cost),
            "average_qualified_price": str(avg_price),
            "justification_status": justification_status
        }
        required_thresholds = {
            "min_estimate_threshold_pct": str(self.est_threshold_pct),
            "estimate_cutoff_price": str(threshold_estimate),
            "min_average_threshold_pct": str(self.avg_threshold_pct),
            "average_cutoff_price": str(threshold_average)
        }

        additional_security = Decimal("0.00")
        is_accepted = True

        if is_abnormal:
            if justification_status == "REJECTED" or not justification_status:
                is_accepted = False
                explanation = (
                    f"Bid rejected as Abnormally Low Bid. Quoted price {format_inr(price)} is below threshold "
                    f"(85% of estimate: {format_inr(threshold_estimate)}, 80% of avg: {format_inr(threshold_average)}). "
                    f"Capacity/cost justification was rejected or not provided."
                )
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bid.bidder_id,
                    rule_id="BR-07",
                    evaluation_stage="ABNORMAL_BID_ANALYSIS",
                    input_values=input_snapshot,
                    required_thresholds=required_thresholds,
                    calculation_details=(
                        f"Price {format_inr(price)} < 85% Estimate ({format_inr(threshold_estimate)}): {triggers_est_shortfall}; "
                        f"Price < 80% Avg ({format_inr(threshold_average)}): {triggers_avg_shortfall}. Justification: REJECTED."
                    ),
                    result="FAIL",
                    human_explanation=explanation,
                    evidence_reference="Rate Analysis Committee Assessment",
                    created_at=now_iso()
                )
                return True, False, Decimal("0.00"), dec
            else:
                # Justification accepted: compute additional performance security based on shortfall
                shortfall_amount = max(Decimal("0.00"), threshold_estimate - price)
                # Shortfall percentage relative to estimated cost
                shortfall_pct = quantize_percent((shortfall_amount / est_cost) * Decimal("100.00"))
                # Additional security amount applied to contract value
                additional_security = quantize_money((price * shortfall_pct) / Decimal("100.00"))

                explanation = (
                    f"Bid flagged as Abnormally Low Bid ({format_inr(price)} < {format_inr(threshold_estimate)}). "
                    f"Detailed price analysis accepted. Imposed {self.abnormal_base_sec_pct}% base performance security "
                    f"plus additional security of {shortfall_pct}% ({format_inr(additional_security)}) to mitigate performance risk."
                )
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bid.bidder_id,
                    rule_id="BR-07",
                    evaluation_stage="ABNORMAL_BID_ANALYSIS",
                    input_values=input_snapshot,
                    required_thresholds=required_thresholds,
                    calculation_details=(
                        f"Shortfall below 85% estimate = {format_inr(shortfall_amount)} ({shortfall_pct}%). "
                        f"Additional Security = ({format_inr(price)} * {shortfall_pct}%) = {format_inr(additional_security)}."
                    ),
                    result="WARNING",
                    human_explanation=explanation,
                    evidence_reference="Accepted Rate Justification & Cost Breakdown",
                    created_at=now_iso()
                )
                return True, True, additional_security, dec
        else:
            explanation = (
                f"Quoted price {format_inr(price)} is within normal commercial range "
                f"(>= 85% estimate of {format_inr(threshold_estimate)} and >= 80% avg of {format_inr(threshold_average)})."
            )
            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=bid.bidder_id,
                rule_id="BR-07",
                evaluation_stage="ABNORMAL_BID_ANALYSIS",
                input_values=input_snapshot,
                required_thresholds=required_thresholds,
                calculation_details=f"Price {format_inr(price)} >= Cutoff {format_inr(threshold_estimate)}",
                result="PASS",
                human_explanation=explanation,
                evidence_reference="Price Distribution Analysis",
                created_at=now_iso()
            )
            return False, True, Decimal("0.00"), dec
