"""
TENDERLENS — Financial Evaluation Engine (BR-04 / FR-06)
Implements arithmetic corrections (unit rate over total), tax/freight normalizations,
and enforces two-envelope cryptographic/logical access protection.
Strictly relies on Python Decimal arithmetic.
"""

import uuid
from decimal import Decimal
from typing import List, Tuple, Dict, Any, Optional
from src.models import Tender, Bid, PriceScheduleItem, FinancialEvaluation, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, format_inr
from src.utils.date_utils import now_iso


class TwoEnvelopeViolationError(Exception):
    """Raised when an attempt is made to evaluate or reveal financial data of an unqualified bidder."""
    pass


class FinancialEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("financial", {})
        self.default_gst_rate = to_decimal(self.config.get("default_gst_rate_pct", "18.00"))

    def evaluate(
        self,
        tender: Tender,
        bid: Bid,
        schedule_items: List[PriceScheduleItem],
        correction_accepted: bool = True
    ) -> Tuple[FinancialEvaluation, List[DecisionRecord]]:
        """
        Evaluates and normalizes price schedules for a technically qualified bidder.
        Raises TwoEnvelopeViolationError if the bidder is not responsive or not qualified.
        """
        # Strict Two-Envelope Protection Check
        if bid.responsiveness_status != "RESPONSIVE":
            raise TwoEnvelopeViolationError(
                f"Two-Envelope Security Violation: Bidder {bid.bidder_id} is NON_RESPONSIVE. "
                "Financial envelope cannot be unlocked or evaluated."
            )
        if bid.technical_status != "QUALIFIED":
            raise TwoEnvelopeViolationError(
                f"Two-Envelope Security Violation: Bidder {bid.bidder_id} is TECHNICALLY_DISQUALIFIED. "
                "Financial envelope must remain strictly locked."
            )

        decisions: List[DecisionRecord] = []
        original_quoted_sum = Decimal("0.00")
        corrected_item_sum = Decimal("0.00")
        tax_additions = Decimal("0.00")
        freight_additions = Decimal("0.00")
        discrepancies = []

        for item in schedule_items:
            orig_item_total = item.quoted_total_amount
            original_quoted_sum += orig_item_total

            # Arithmetic verification: Quantity * Unit Rate
            calc_item_total = quantize_money(item.quantity * item.quoted_unit_rate)
            corrected_item_sum += calc_item_total

            if calc_item_total != orig_item_total:
                diff = calc_item_total - orig_item_total
                disc_msg = (
                    f"Item {item.item_no} ({item.description}): Quoted Total {format_inr(orig_item_total)} "
                    f"differs from Unit Rate calculation ({item.quantity} {item.unit} @ {format_inr(item.quoted_unit_rate)} = {format_inr(calc_item_total)}). "
                    f"Discrepancy: {format_inr(diff)}."
                )
                discrepancies.append(disc_msg)

            # GST normalization: If GST excluded, add GST
            item_base_price = calc_item_total
            if not item.is_gst_included:
                gst_pct = item.gst_rate_pct if item.gst_rate_pct > Decimal("0.00") else self.default_gst_rate
                gst_val = quantize_money((item_base_price * gst_pct) / Decimal("100.00"))
                tax_additions += gst_val

            # Freight normalization: If freight excluded, add freight amount
            if not item.is_freight_included:
                freight_additions += item.freight_amount

        has_discrepancy = len(discrepancies) > 0
        discrepancy_details = "\n".join(discrepancies) if has_discrepancy else None

        # Base tax & freight adjusted totals
        base_tax_adjusted = corrected_item_sum + tax_additions
        final_comparative_price = base_tax_adjusted + freight_additions

        # Decision Record: Arithmetic Correction
        arith_result = "PASS" if not has_discrepancy or correction_accepted else "FAIL"
        arith_expl = (
            f"Arithmetic verification passed. Total matches unit rate calculations: {format_inr(corrected_item_sum)}."
            if not has_discrepancy else
            f"Arithmetic corrections applied using unit rates over totals: Original {format_inr(original_quoted_sum)} -> Corrected {format_inr(corrected_item_sum)}. Correction accepted by bidder: {correction_accepted}."
        )

        dec_arith = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bid.bidder_id,
            rule_id="BR-04",
            evaluation_stage="FINANCIAL_EVALUATION",
            input_values={
                "original_quoted_total": str(original_quoted_sum),
                "items_count": len(schedule_items),
                "correction_accepted": correction_accepted
            },
            required_thresholds={"priority": "UNIT_RATE_OVER_TOTAL"},
            calculation_details=discrepancy_details or f"Verified sum of (Quantity * Unit Rate) = {format_inr(corrected_item_sum)}",
            result=arith_result,
            human_explanation=arith_expl,
            evidence_reference="Price Schedule Analysis Sheet",
            created_at=now_iso()
        )
        decisions.append(dec_arith)

        # Decision Record: Commercial Normalization
        dec_norm = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bid.bidder_id,
            rule_id="BR-04",
            evaluation_stage="FINANCIAL_EVALUATION",
            input_values={
                "corrected_base_price": str(corrected_item_sum),
                "tax_additions": str(tax_additions),
                "freight_additions": str(freight_additions)
            },
            required_thresholds={"normalization_basis": "All-inclusive Common Footing (FOR Destination)"},
            calculation_details=(
                f"Final Price = Corrected Base ({format_inr(corrected_item_sum)}) + "
                f"Taxes ({format_inr(tax_additions)}) + Freight ({format_inr(freight_additions)}) = {format_inr(final_comparative_price)}"
            ),
            result="PASS",
            human_explanation=f"Bid normalized to common comparison basis at {format_inr(final_comparative_price)} inclusive of duties, taxes and freight.",
            evidence_reference="Commercial Normalization Summary",
            created_at=now_iso()
        )
        decisions.append(dec_norm)

        eval_result = FinancialEvaluation(
            eval_id=str(uuid.uuid4()),
            bid_id=bid.bid_id,
            original_quoted_total=original_quoted_sum,
            arithmetic_corrected_total=corrected_item_sum,
            has_arithmetic_discrepancy=has_discrepancy,
            arithmetic_discrepancy_details=discrepancy_details,
            correction_accepted=correction_accepted,
            base_tax_adjusted_total=base_tax_adjusted,
            freight_adjusted_total=final_comparative_price,
            final_comparative_price=final_comparative_price,
            financial_score=None,
            combined_qcbs_score=None,
            is_abnormally_low=False,
            abnormal_justification_status=None,
            additional_security_required=Decimal("0.00"),
            evaluated_at=now_iso()
        )

        return eval_result, decisions
