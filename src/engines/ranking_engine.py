"""
TENDERLENS — Ranking and QCBS Engine (BR-06 / FR-08)
Implements Least Cost System (LCS) and Quality and Cost Based Selection (QCBS).
Computes inverse proportional financial scores and composite weighted scores with documented tie-breakers.
"""

import uuid
from decimal import Decimal
from typing import List, Tuple, Dict, Any
from src.models import Tender, Bid, FinancialEvaluation, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_percent, quantize_money, format_inr
from src.utils.date_utils import now_iso


class RankingEngine:
    def __init__(self, scoring_config: Dict[str, Any]):
        self.default_qcbs = scoring_config.get("default_qcbs", {})
        self.default_tech_weight = to_decimal(self.default_qcbs.get("technical_weight", "70.00"))
        self.default_fin_weight = to_decimal(self.default_qcbs.get("financial_weight", "30.00"))

    def rank_bids(
        self,
        tender: Tender,
        qualified_bids: List[Tuple[Bid, FinancialEvaluation]]
    ) -> Tuple[List[Tuple[Bid, FinancialEvaluation, int]], List[DecisionRecord]]:
        """
        Ranks qualified bids based on tender evaluation method (LCS or QCBS).
        Returns: (ranked_list_with_ranks, list_of_decisions)
        """
        decisions: List[DecisionRecord] = []
        if not qualified_bids:
            return [], decisions

        # Identify absolute lowest price (L1) among qualified bids
        lowest_eval = min(qualified_bids, key=lambda x: x[1].final_comparative_price)[1]
        l1_price = lowest_eval.final_comparative_price

        method = tender.evaluation_method.upper()
        ranked_results = []

        if method == "LCS":
            # Sort primary by price ASC, secondary by technical score DESC, tertiary by timestamp ASC
            sorted_bids = sorted(
                qualified_bids,
                key=lambda x: (
                    x[1].final_comparative_price,
                    -x[0].overall_technical_score,
                    x[0].submission_timestamp
                )
            )

            for rank_idx, (bid, ev) in enumerate(sorted_bids, start=1):
                bid.final_rank = rank_idx
                ranked_results.append((bid, ev, rank_idx))

                is_l1 = (rank_idx == 1)
                expl = (
                    f"Bidder achieved Rank L{rank_idx} under LCS. Final comparative price: {format_inr(ev.final_comparative_price)}."
                    if not is_l1 else
                    f"Bidder determined as L1 (Lowest Evaluated Responsive Bidder) under LCS with evaluated price {format_inr(ev.final_comparative_price)}."
                )

                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bid.bidder_id,
                    rule_id="BR-06",
                    evaluation_stage="RANKING",
                    input_values={"evaluated_price": str(ev.final_comparative_price), "technical_score": str(bid.overall_technical_score)},
                    required_thresholds={"method": "LCS"},
                    calculation_details=f"Rank {rank_idx} assigned based on price ordering (Tie-breaker: Technical score).",
                    result="PASS",
                    human_explanation=expl,
                    evidence_reference="LCS Financial Comparative Matrix",
                    created_at=now_iso()
                )
                decisions.append(dec)

        elif method == "QCBS":
            tech_weight = tender.qcbs_tech_weight if tender.qcbs_tech_weight > Decimal("0.00") else self.default_tech_weight
            fin_weight = tender.qcbs_fin_weight if tender.qcbs_fin_weight > Decimal("0.00") else self.default_fin_weight

            scored_bids = []
            for bid, ev in qualified_bids:
                bidder_price = ev.final_comparative_price
                # Financial Score = (L1 / Price) * 100
                if bidder_price > Decimal("0.00"):
                    fin_score = quantize_percent((l1_price / bidder_price) * Decimal("100.00"))
                else:
                    fin_score = Decimal("0.00")

                ev.financial_score = fin_score

                # Composite score = (TechScore * TechWeight / 100) + (FinScore * FinWeight / 100)
                tech_contrib = quantize_percent((bid.overall_technical_score * tech_weight) / Decimal("100.00"))
                fin_contrib = quantize_percent((fin_score * fin_weight) / Decimal("100.00"))
                composite_score = quantize_percent(tech_contrib + fin_contrib)
                ev.combined_qcbs_score = composite_score

                scored_bids.append((bid, ev, composite_score, tech_contrib, fin_contrib))

            # Sort primary by composite score DESC, secondary by price ASC, tertiary by technical score DESC
            sorted_bids = sorted(
                scored_bids,
                key=lambda x: (
                    -x[2],                          # Highest composite score wins
                    x[1].final_comparative_price,   # Tie-breaker 1: Lower price
                    -x[0].overall_technical_score,  # Tie-breaker 2: Higher technical score
                    x[0].submission_timestamp       # Tie-breaker 3: Submission timestamp
                )
            )

            for rank_idx, (bid, ev, comp_score, t_contrib, f_contrib) in enumerate(sorted_bids, start=1):
                bid.final_rank = rank_idx
                ranked_results.append((bid, ev, rank_idx))

                is_h1 = (rank_idx == 1)
                expl = (
                    f"Bidder achieved Rank H{rank_idx} under QCBS ({tech_weight}:{fin_weight}) with composite score {comp_score} "
                    f"(Technical: {bid.overall_technical_score} -> {t_contrib}, Financial: {ev.financial_score} -> {f_contrib})."
                    if not is_h1 else
                    f"Bidder selected as H1 highest composite scorer under QCBS with score {comp_score}."
                )

                dec = DecisionRecord(
                    decision_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bid.bidder_id,
                    rule_id="BR-06",
                    evaluation_stage="RANKING",
                    input_values={
                        "technical_score": str(bid.overall_technical_score),
                        "financial_price": str(ev.final_comparative_price),
                        "l1_price": str(l1_price)
                    },
                    required_thresholds={"method": "QCBS", "tech_weight": str(tech_weight), "fin_weight": str(fin_weight)},
                    calculation_details=(
                        f"Financial Score = ({format_inr(l1_price)} / {format_inr(ev.final_comparative_price)}) * 100 = {ev.financial_score}. "
                        f"Composite = ({bid.overall_technical_score} * {tech_weight}%) + ({ev.financial_score} * {fin_weight}%) = {comp_score}."
                    ),
                    result="PASS",
                    human_explanation=expl,
                    evidence_reference="QCBS Comparative Evaluation Sheet",
                    created_at=now_iso()
                )
                decisions.append(dec)

        return ranked_results, decisions
