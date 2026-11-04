"""
TENDERLENS — EMD Evaluation Engine (BR-02 / FR-04)
Evaluates Earnest Money Deposit (EMD) requirements, exemptions (MSE, Startup),
and Bank Guarantee validity horizons with mandatory boundary condition checking.
"""

import uuid
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional
from src.models import Tender, Bidder, Bid, EMDRecord, BidderCertificate, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, format_inr
from src.utils.date_utils import parse_date, add_days, days_between, now_iso


class EMDEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("emd", {})
        self.rate_pct = to_decimal(self.config.get("rate_pct_of_estimate", "2.00"))
        self.max_cap = to_decimal(self.config.get("max_emd_amount", "5000000.00"))
        self.bg_extra_days = int(self.config.get("bg_validity_extra_days", 45))

    def calculate_required_emd(self, estimated_cost: Decimal) -> Decimal:
        """Calculates 2% of estimated cost capped at 50 Lakhs."""
        calc = quantize_money((estimated_cost * self.rate_pct) / Decimal("100.00"))
        return min(calc, self.max_cap)

    def evaluate(
        self,
        tender: Tender,
        bidder: Bidder,
        emd_record: Optional[EMDRecord],
        certificates: list
    ) -> Tuple[bool, str, DecisionRecord]:
        """
        Evaluates EMD submission.
        Returns: (is_valid, status_code, decision_record)
        """
        required_emd = tender.emd_amount if tender.emd_amount > Decimal("0.00") else self.calculate_required_emd(tender.estimated_cost)
        bid_validity_end = add_days(tender.bid_opening_date, tender.bid_validity_days)
        min_bg_validity = add_days(bid_validity_end, self.bg_extra_days)

        input_snapshot = {
            "tender_id": tender.tender_id,
            "bidder_id": bidder.bidder_id,
            "estimated_cost": str(tender.estimated_cost),
            "emd_record_present": emd_record is not None,
            "bid_validity_days": tender.bid_validity_days,
            "bid_opening_date": tender.bid_opening_date
        }
        required_thresholds = {
            "required_emd_amount": str(required_emd),
            "bg_extra_days_required": self.bg_extra_days,
            "min_bg_validity_date": min_bg_validity,
            "exemptions_allowed": ["MSE", "STARTUP"]
        }

        # Check exemption
        if emd_record and emd_record.exemption_claimed:
            cat = (emd_record.exemption_category or "").upper()
            valid_cert = any(
                c.cert_type == cat and c.is_valid for c in certificates
            )
            if valid_cert:
                explanation = f"EMD Exemption granted for {cat} under valid certificate. Required EMD {format_inr(required_emd)} waived."
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bidder.bidder_id,
                    rule_id="BR-02",
                    evaluation_stage="TIMELINE_AND_EMD",
                    input_values=input_snapshot,
                    required_thresholds=required_thresholds,
                    calculation_details=f"Exemption category '{cat}' verified against valid certificate.",
                    result="PASS",
                    human_explanation=explanation,
                    evidence_reference=f"Certificate type: {cat}",
                    created_at=now_iso()
                )
                return True, "VALID", dec
            else:
                explanation = f"EMD Exemption claimed as {cat} but no valid supporting certificate was provided."
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bidder.bidder_id,
                    rule_id="BR-02",
                    evaluation_stage="TIMELINE_AND_EMD",
                    input_values=input_snapshot,
                    required_thresholds=required_thresholds,
                    calculation_details=f"Exemption claim '{cat}' failed: missing/invalid certificate.",
                    result="FAIL",
                    human_explanation=explanation,
                    evidence_reference="Missing valid certificate",
                    created_at=now_iso()
                )
                return False, "INVALID", dec

        # Check physical/financial EMD payment
        if not emd_record or emd_record.amount_paid < required_emd:
            paid_str = format_inr(emd_record.amount_paid) if emd_record else "₹0.00"
            explanation = f"Insufficient EMD submitted. Paid {paid_str}, whereas required amount is {format_inr(required_emd)}."
            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=bidder.bidder_id,
                rule_id="BR-02",
                evaluation_stage="TIMELINE_AND_EMD",
                input_values=input_snapshot,
                required_thresholds=required_thresholds,
                calculation_details=f"Paid {paid_str} < Required {format_inr(required_emd)}",
                result="FAIL",
                human_explanation=explanation,
                evidence_reference=emd_record.instrument_reference if emd_record else "No instrument",
                created_at=now_iso()
            )
            return False, "INVALID", dec

        # If BG mode, verify validity horizon
        if emd_record.payment_mode == "BG":
            if not emd_record.valid_until:
                explanation = "Bank Guarantee submitted without valid_until date."
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bidder.bidder_id,
                    rule_id="BR-02",
                    evaluation_stage="TIMELINE_AND_EMD",
                    input_values=input_snapshot,
                    required_thresholds=required_thresholds,
                    calculation_details="BG validity date missing.",
                    result="FAIL",
                    human_explanation=explanation,
                    evidence_reference=emd_record.instrument_reference,
                    created_at=now_iso()
                )
                return False, "INVALID", dec

            days_beyond = days_between(bid_validity_end, emd_record.valid_until)
            # Mandatory boundary condition: exactly 45 additional days must PASS
            if days_beyond < self.bg_extra_days:
                explanation = (
                    f"Bank Guarantee validity insufficient. Valid until {emd_record.valid_until} "
                    f"({days_beyond} days beyond bid validity date {bid_validity_end}), "
                    f"minimum required is {self.bg_extra_days} days."
                )
                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bidder.bidder_id,
                    rule_id="BR-02",
                    evaluation_stage="TIMELINE_AND_EMD",
                    input_values=input_snapshot,
                    required_thresholds=required_thresholds,
                    calculation_details=f"BG days beyond bid validity: {days_beyond} < {self.bg_extra_days}",
                    result="FAIL",
                    human_explanation=explanation,
                    evidence_reference=f"BG Valid until {emd_record.valid_until}",
                    created_at=now_iso()
                )
                return False, "INVALID", dec

        explanation = f"EMD requirement fully satisfied. Paid {format_inr(emd_record.amount_paid)} via {emd_record.payment_mode}."
        dec = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bidder.bidder_id,
            rule_id="BR-02",
            evaluation_stage="TIMELINE_AND_EMD",
            input_values=input_snapshot,
            required_thresholds=required_thresholds,
            calculation_details=f"Paid {format_inr(emd_record.amount_paid)} >= {format_inr(required_emd)}",
            result="PASS",
            human_explanation=explanation,
            evidence_reference=emd_record.instrument_reference,
            created_at=now_iso()
        )
        return True, "VALID", dec
