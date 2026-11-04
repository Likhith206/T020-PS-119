"""
TENDERLENS — Award and Performance Security Engine (BR-09 / FR-11)
Issues Letter of Acceptance (LoA), calculates standard (3%) vs abnormal-low (5% + additional)
performance securities, tracks 21-day submission deadline, enforces EMD forfeiture on default,
and manages fallback to next-ranked bidder (within 10% of L1) or re-tender.
"""

import uuid
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional
from src.models import Tender, Bid, FinancialEvaluation, Award, PerformanceSecurity, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, format_inr
from src.utils.date_utils import add_days, is_on_or_before, now_iso, today_iso


class AwardEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("award", {})
        self.std_security_pct = to_decimal(self.config.get("standard_performance_security_pct", "3.00"))
        self.abnormal_security_pct = to_decimal(self.config.get("abnormal_performance_security_pct", "5.00"))
        self.submission_window_days = int(self.config.get("security_submission_window_days", 21))
        self.next_match_margin_pct = to_decimal(self.config.get("next_bidder_match_margin_pct", "10.00"))

    def create_award(
        self,
        tender: Tender,
        winning_bid: Bid,
        evaluation: FinancialEvaluation,
        loa_date: Optional[str] = None
    ) -> Tuple[Award, PerformanceSecurity, DecisionRecord]:
        """Creates formal LoA and required Performance Security structure."""
        issue_date = loa_date or today_iso()
        security_due = add_days(issue_date, self.submission_window_days)
        contract_value = evaluation.final_comparative_price

        # Check if bid was flagged abnormally low
        if evaluation.is_abnormally_low:
            sec_rate = self.abnormal_security_pct
            std_amount = quantize_money((contract_value * sec_rate) / Decimal("100.00"))
            add_amount = evaluation.additional_security_required
        else:
            sec_rate = self.std_security_pct
            std_amount = quantize_money((contract_value * sec_rate) / Decimal("100.00"))
            add_amount = Decimal("0.00")

        total_sec = std_amount + add_amount
        award_id = f"AWD_{tender.tender_id}"
        loa_ref = f"LOA/{tender.tender_id}/{winning_bid.bidder_id}/{issue_date[:4]}"

        award = Award(
            award_id=award_id,
            tender_id=tender.tender_id,
            awarded_bidder_id=winning_bid.bidder_id,
            contract_value=contract_value,
            award_method=tender.evaluation_method,
            loa_reference=loa_ref,
            loa_issue_date=issue_date,
            security_due_date=security_due,
            status="LOA_ISSUED",
            created_at=now_iso()
        )

        security = PerformanceSecurity(
            security_id=f"SEC_{award_id}",
            award_id=award_id,
            standard_security_rate_pct=sec_rate,
            standard_security_amount=std_amount,
            additional_security_amount=add_amount,
            total_security_required=total_sec,
            submitted_amount=Decimal("0.00"),
            status="PENDING",
            created_at=now_iso()
        )

        dec = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=winning_bid.bidder_id,
            rule_id="BR-09",
            evaluation_stage="AWARD_AND_SECURITY",
            input_values={
                "contract_value": str(contract_value),
                "is_abnormal_low": evaluation.is_abnormally_low,
                "loa_issue_date": issue_date
            },
            required_thresholds={
                "standard_security_rate_pct": str(sec_rate),
                "total_security_required": str(total_sec),
                "security_due_date": security_due
            },
            calculation_details=(
                f"Base Security ({sec_rate}%) = {format_inr(std_amount)} + "
                f"Additional Security = {format_inr(add_amount)}. Total = {format_inr(total_sec)}."
            ),
            result="PASS",
            human_explanation=(
                f"Contract awarded to {winning_bid.bidder_id}. Letter of Acceptance issued ({loa_ref}). "
                f"Performance security of {format_inr(total_sec)} due within 21 days ({security_due})."
            ),
            evidence_reference=loa_ref,
            created_at=now_iso()
        )

        return award, security, dec

    def process_security_default(
        self,
        tender: Tender,
        award: Award,
        l1_price: Decimal,
        next_ranked_bid: Optional[Bid],
        next_eval: Optional[FinancialEvaluation]
    ) -> Tuple[str, str, DecisionRecord]:
        """
        Handles breach when awarded bidder fails to submit performance security within 21 days.
        Triggers EMD forfeiture and evaluates fallback or re-tender.
        """
        award.status = "DEFAULTED"
        margin_price = quantize_money(l1_price * (Decimal("1.00") + (self.next_match_margin_pct / Decimal("100.00"))))

        if next_ranked_bid and next_eval:
            next_price = next_eval.final_comparative_price
            if next_price <= margin_price:
                # Offer to next bidder at their own price
                explanation = (
                    f"Awardee {award.awarded_bidder_id} failed to submit performance security. EMD forfeited. "
                    f"Next ranked bidder {next_ranked_bid.bidder_id} price {format_inr(next_price)} is within 10% of L1 "
                    f"({format_inr(margin_price)}). Offering contract to L2."
                )
                action = "OFFER_TO_NEXT_BIDDER"
                res = "WARNING"
            else:
                explanation = (
                    f"Awardee {award.awarded_bidder_id} failed to submit security. EMD forfeited. "
                    f"Next ranked bidder price {format_inr(next_price)} exceeds 10% margin ({format_inr(margin_price)}). "
                    "Triggering re-tender."
                )
                action = "TRIGGER_RETENDER"
                res = "FAIL"
        else:
            explanation = (
                f"Awardee {award.awarded_bidder_id} defaulted on security. EMD forfeited. "
                "No subsequent qualified bidder available. Triggering re-tender."
            )
            action = "TRIGGER_RETENDER"
            res = "FAIL"

        dec = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=award.awarded_bidder_id,
            rule_id="BR-09",
            evaluation_stage="AWARD_AND_SECURITY",
            input_values={"defaulted_bidder": award.awarded_bidder_id, "l1_price": str(l1_price)},
            required_thresholds={"next_margin_pct": str(self.next_match_margin_pct), "margin_cutoff": str(margin_price)},
            calculation_details=f"Forfeited EMD. Evaluated next bidder availability and 10% price window: Action = {action}",
            result=res,
            human_explanation=explanation,
            evidence_reference="Default Notice & Forfeiture Order",
            created_at=now_iso()
        )

        return action, explanation, dec
