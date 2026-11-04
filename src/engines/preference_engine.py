"""
TENDERLENS — Public Procurement Preference Engine (BR-05 / FR-07)
Enforces Public Procurement Policy for MSEs (25% split, 15% margin band) and
Make in India Order (Class-I local supplier >= 50% local content, 20% margin band, 50% split).
Handles 100% reserved item allocation and precedence hierarchy (MSE first, then Class-I).
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Tuple, Any, Optional
from src.models import Tender, Bid, Bidder, BidderCertificate, FinancialEvaluation, PreferenceAllocation, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_money, quantize_percent, format_inr
from src.utils.date_utils import now_iso


class PreferenceEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("preferences", {})
        self.mse_margin_pct = to_decimal(self.config.get("mse_margin_pct_above_l1", "15.00"))
        self.mse_max_qty_pct = to_decimal(self.config.get("mse_max_quantity_pct", "25.00"))
        self.class1_content_min_pct = to_decimal(self.config.get("class_1_local_content_min_pct", "50.00"))
        self.class1_margin_pct = to_decimal(self.config.get("class_1_margin_pct_above_l1", "20.00"))
        self.class1_max_qty_pct = to_decimal(self.config.get("class_1_max_quantity_pct", "50.00"))

    def evaluate_preferences(
        self,
        tender: Tender,
        l1_bid: Bid,
        l1_eval: FinancialEvaluation,
        other_evals: List[Tuple[Bid, FinancialEvaluation, Bidder, List[BidderCertificate]]]
    ) -> Tuple[List[PreferenceAllocation], List[DecisionRecord]]:
        """
        Evaluates preference allocations for all qualified bidders relative to L1.
        Preserves base L1 ranking while producing purchase preference splits.
        """
        allocations: List[PreferenceAllocation] = []
        decisions: List[DecisionRecord] = []
        l1_price = l1_eval.final_comparative_price

        # Threshold limits: L1 + 15% for MSE, L1 + 20% for Make-in-India
        mse_upper_bound = quantize_money(l1_price * (Decimal("1.00") + (self.mse_margin_pct / Decimal("100.00"))))
        class1_upper_bound = quantize_money(l1_price * (Decimal("1.00") + (self.class1_margin_pct / Decimal("100.00"))))

        # Check if item is 100% reserved for MSE
        is_reserved = tender.is_reserved_item

        # 1. Base L1 allocation
        initial_l1_qty = Decimal("0.00") if is_reserved else Decimal("100.00")
        l1_alloc = PreferenceAllocation(
            allocation_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=l1_bid.bidder_id,
            preference_type="NONE",
            is_l1_matched=True,
            allocated_quantity_pct=initial_l1_qty,
            awarded_price=l1_price,
            rationale="Original lowest evaluated responsive bidder (L1).",
            created_at=now_iso()
        )
        allocations.append(l1_alloc)

        # 2. Identify eligible MSE bidders within L1 + 15%
        mse_candidates = []
        for bid, ev, bidder, certs in other_evals:
            has_mse_cert = any(c.cert_type == "MSE" and c.is_valid for c in certs)
            # Mandatory boundary condition: exactly 15% above L1 must qualify (<= mse_upper_bound)
            if has_mse_cert and ev.final_comparative_price <= mse_upper_bound:
                mse_candidates.append((bid, ev, bidder))

        # Sort MSE candidates by price ascending
        mse_candidates.sort(key=lambda x: x[1].final_comparative_price)

        allocated_mse_qty = Decimal("0.00")
        if mse_candidates:
            selected_mse_bid, selected_mse_ev, selected_mse_bidder = mse_candidates[0]
            target_qty = Decimal("100.00") if is_reserved else self.mse_max_qty_pct
            allocated_mse_qty = target_qty

            alloc_mse = PreferenceAllocation(
                allocation_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=selected_mse_bidder.bidder_id,
                preference_type="MSE",
                is_l1_matched=True,
                allocated_quantity_pct=target_qty,
                awarded_price=l1_price,
                rationale=(
                    f"MSE Preference applied under Public Procurement Policy: Bidder within 15% of L1 "
                    f"({format_inr(selected_mse_ev.final_comparative_price)} <= {format_inr(mse_upper_bound)}). "
                    f"Allocated {target_qty}% quantity at matched L1 rate {format_inr(l1_price)}."
                ),
                created_at=now_iso()
            )
            allocations.append(alloc_mse)

            # Reduce L1 allocation accordingly
            l1_alloc.allocated_quantity_pct = max(Decimal("0.00"), Decimal("100.00") - allocated_mse_qty)

            dec_mse = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=selected_mse_bidder.bidder_id,
                rule_id="BR-05",
                evaluation_stage="PROCUREMENT_PREFERENCES",
                input_values={"bidder_price": str(selected_mse_ev.final_comparative_price), "l1_price": str(l1_price), "is_mse": True},
                required_thresholds={"mse_margin_pct": str(self.mse_margin_pct), "max_margin_price": str(mse_upper_bound)},
                calculation_details=f"Price {format_inr(selected_mse_ev.final_comparative_price)} <= {format_inr(mse_upper_bound)} (L1 + 15%). Matched L1 rate.",
                result="PASS",
                human_explanation=f"MSE bidder {selected_mse_bidder.bidder_id} matched L1 price and received {target_qty}% quantity allocation.",
                evidence_reference="MSE Udyam Registration Certificate",
                created_at=now_iso()
            )
            decisions.append(dec_mse)

        # 3. If not 100% reserved, identify Class-I Local Suppliers for remaining quantity
        if not is_reserved and (Decimal("100.00") - allocated_mse_qty) > Decimal("0.00"):
            class1_candidates = []
            for bid, ev, bidder, certs in other_evals:
                # Exclude bidder already allocated via MSE
                if any(a.bidder_id == bidder.bidder_id for a in allocations if a.preference_type == "MSE"):
                    continue
                # Verify Class-I status: Local content >= 50%
                class1_cert = next(
                    (c for c in certs if c.cert_type == "MAKE_IN_INDIA" and c.is_valid and c.local_content_percentage >= self.class1_content_min_pct),
                    None
                )
                if class1_cert and ev.final_comparative_price <= class1_upper_bound:
                    class1_candidates.append((bid, ev, bidder, class1_cert))

            class1_candidates.sort(key=lambda x: x[1].final_comparative_price)

            if class1_candidates:
                c1_bid, c1_ev, c1_bidder, c1_cert = class1_candidates[0]
                # Available capacity is up to 50% of total
                remaining_qty = Decimal("100.00") - allocated_mse_qty
                c1_qty = min(self.class1_max_qty_pct, remaining_qty)

                alloc_c1 = PreferenceAllocation(
                    allocation_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=c1_bidder.bidder_id,
                    preference_type="MAKE_IN_INDIA",
                    is_l1_matched=True,
                    allocated_quantity_pct=c1_qty,
                    awarded_price=l1_price,
                    rationale=(
                        f"Make in India (Class-I) Preference: Local content {c1_cert.local_content_percentage}% (>= 50%). "
                        f"Bid within 20% margin ({format_inr(c1_ev.final_comparative_price)} <= {format_inr(class1_upper_bound)}). "
                        f"Allocated {c1_qty}% quantity at matched L1 price."
                    ),
                    created_at=now_iso()
                )
                allocations.append(alloc_c1)
                l1_alloc.allocated_quantity_pct = max(Decimal("0.00"), Decimal("100.00") - allocated_mse_qty - c1_qty)

                dec_c1 = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=c1_bidder.bidder_id,
                    rule_id="BR-05",
                    evaluation_stage="PROCUREMENT_PREFERENCES",
                    input_values={"local_content_pct": str(c1_cert.local_content_percentage), "bidder_price": str(c1_ev.final_comparative_price)},
                    required_thresholds={"min_local_content_pct": str(self.class1_content_min_pct), "margin_pct": str(self.class1_margin_pct)},
                    calculation_details=f"Local content {c1_cert.local_content_percentage}% >= 50%, Price {format_inr(c1_ev.final_comparative_price)} <= {format_inr(class1_upper_bound)}",
                    result="PASS",
                    human_explanation=f"Class-I supplier {c1_bidder.bidder_id} matched L1 price and received {c1_qty}% quantity allocation.",
                    evidence_reference="Make in India Local Content Declaration",
                    created_at=now_iso()
                )
                decisions.append(dec_c1)

        return allocations, decisions
