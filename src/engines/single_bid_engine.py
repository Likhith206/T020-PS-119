"""
TENDERLENS — Single Bid and Re-tender Engine (BR-10 / FR-12)
Enforces competition safeguards when only a single responsive bid is received.
Permits award only if single_bid_allowed is explicitly enabled; otherwise triggers re-tender.
"""

import uuid
from typing import Tuple, List, Dict, Any
from src.models import Tender, Bid, DecisionRecord
from src.utils.date_utils import now_iso


class SingleBidEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config

    def evaluate_competition(
        self,
        tender: Tender,
        responsive_bids: List[Bid]
    ) -> Tuple[bool, str, DecisionRecord]:
        """
        Evaluates whether adequate competition exists or single-bid award/re-tender is triggered.
        Returns: (can_proceed, action_code, decision_record)
        """
        count = len(responsive_bids)
        input_snapshot = {
            "tender_id": tender.tender_id,
            "responsive_bids_count": count,
            "single_bid_allowed": tender.single_bid_allowed
        }

        if count == 0:
            expl = "No responsive bids found after technical and responsiveness evaluation. Mandatory re-tender triggered."
            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=None,
                rule_id="BR-10",
                evaluation_stage="RANKING",
                input_values=input_snapshot,
                required_thresholds={"min_responsive_bids": 1},
                calculation_details="Responsive count = 0 -> Automatic re-tender.",
                result="FAIL",
                human_explanation=expl,
                evidence_reference="Procurement Committee Evaluation Summary",
                created_at=now_iso()
            )
            return False, "RETENDER_NO_BIDS", dec

        elif count == 1:
            if tender.single_bid_allowed:
                expl = (
                    "Single responsive bid received. Proceeding with evaluation and award as "
                    "SINGLE_BID_ALLOWED is explicitly enabled in tender terms."
                )
                res = "PASS"
                action = "PROCEED_SINGLE_BID"
            else:
                expl = (
                    "Single responsive bid received. Lack of competition detected and "
                    "SINGLE_BID_ALLOWED is disabled. Re-tender is mandatory."
                )
                res = "FAIL"
                action = "TRIGGER_RETENDER"

            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=responsive_bids[0].bidder_id,
                rule_id="BR-10",
                evaluation_stage="RANKING",
                input_values=input_snapshot,
                required_thresholds={"single_bid_allowed": tender.single_bid_allowed},
                calculation_details=f"Responsive count = 1. Single Bid Allowed: {tender.single_bid_allowed}.",
                result=res,
                human_explanation=expl,
                evidence_reference="Competition Assessment Note",
                created_at=now_iso()
            )
            return tender.single_bid_allowed, action, dec

        else:
            expl = f"Sufficient competition established with {count} responsive bids."
            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=None,
                rule_id="BR-10",
                evaluation_stage="RANKING",
                input_values=input_snapshot,
                required_thresholds={"min_responsive_bids": 2},
                calculation_details=f"Responsive count = {count} >= 2.",
                result="PASS",
                human_explanation=expl,
                evidence_reference="Competition Assessment Note",
                created_at=now_iso()
            )
            return True, "COMPETITION_SATISFIED", dec
