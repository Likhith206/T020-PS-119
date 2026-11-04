"""
TENDERLENS — Bid Validity and Extension Engine (BR-08 / FR-10)
Enforces calendar-day validity tracking, 30-day single extension requests,
and non-punitive exit upon refusal (no EMD forfeiture).
"""

import uuid
from typing import Tuple, Dict, Any, Optional
from src.models import Tender, Bid, DecisionRecord
from src.utils.date_utils import parse_date, add_days, is_on_or_before, now_iso, today_iso


class ValidityEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("validity", {})
        self.default_validity_days = int(self.config.get("default_bid_validity_days", 90))
        self.max_extension_days = int(self.config.get("max_extension_days", 30))

    def evaluate_validity(
        self,
        tender: Tender,
        bid: Bid,
        as_of_date: Optional[str] = None,
        extension_response: Optional[str] = None
    ) -> Tuple[bool, str, str, DecisionRecord]:
        """
        Evaluates whether a bid remains legally valid.
        Returns: (is_valid, status_code, current_expiry_date, decision_record)
        """
        eval_date = as_of_date or today_iso()
        validity_days = tender.bid_validity_days or self.default_validity_days
        original_expiry = add_days(tender.bid_opening_date, validity_days)

        current_expiry = original_expiry
        if extension_response == "ACCEPTED":
            current_expiry = add_days(original_expiry, self.max_extension_days)

        # Boundary condition: Day 90 is valid (eval_date <= current_expiry)
        is_still_valid = is_on_or_before(eval_date, current_expiry)

        if extension_response == "REJECTED":
            status_code = "EXITED_NO_FORFEITURE"
            explanation = (
                f"Bidder declined validity extension beyond {original_expiry}. "
                "Permitted clean exit without EMD forfeiture as per public procurement norms."
            )
            res = "SKIPPED"
        elif is_still_valid:
            status_code = "VALID"
            explanation = f"Bid is legally valid as of {eval_date} (Expiry horizon: {current_expiry})."
            res = "PASS"
        else:
            status_code = "EXPIRED"
            explanation = f"Bid validity expired on {current_expiry}. Award after this date is VOID without formal extension."
            res = "FAIL"

        dec = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bid.bidder_id,
            rule_id="BR-08",
            evaluation_stage="BID_VALIDITY",
            input_values={
                "as_of_date": eval_date,
                "original_expiry": original_expiry,
                "extension_response": extension_response
            },
            required_thresholds={"current_expiry_date": current_expiry},
            calculation_details=f"Eval Date {eval_date} <= Current Expiry {current_expiry}: {is_still_valid}",
            result=res,
            human_explanation=explanation,
            evidence_reference="Tender Bid Validity Register",
            created_at=now_iso()
        )

        return (is_still_valid and extension_response != "REJECTED"), status_code, current_expiry, dec
