"""
TENDERLENS — Technical Evaluation Engine (BR-03 / FR-05)
Evaluates evaluator scores across criteria, computes weighted averages,
and enforces minimum individual (60%) and overall (70%) cut-offs.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Tuple, Any
from src.models import Tender, Bid, TechnicalCriterion, TechnicalScore, DecisionRecord
from src.utils.money_utils import to_decimal, quantize_percent
from src.utils.date_utils import now_iso


class TechnicalEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.config = rules_config.get("technical", {})
        self.min_individual_pct = to_decimal(self.config.get("min_individual_criterion_pct", "60.00"))
        self.min_overall_pct = to_decimal(self.config.get("min_overall_technical_pct", "70.00"))

    def evaluate(
        self,
        tender: Tender,
        bid: Bid,
        criteria: List[TechnicalCriterion],
        scores: List[TechnicalScore]
    ) -> Tuple[bool, Decimal, Dict[str, Decimal], List[DecisionRecord]]:
        """
        Evaluates technical performance across criteria.
        Returns: (is_qualified, overall_score, dict_criterion_scores, list_of_decisions)
        """
        decisions: List[DecisionRecord] = []
        criterion_scores: Dict[str, Decimal] = {}
        weighted_sum = Decimal("0.00")
        all_individual_pass = True

        for crit in criteria:
            crit_scores = [s.raw_score for s in scores if s.criterion_id == crit.criterion_id]
            if not crit_scores:
                avg_score = Decimal("0.00")
            else:
                avg_score = quantize_percent(sum(crit_scores) / Decimal(len(crit_scores)))

            criterion_scores[crit.code] = avg_score
            min_required = crit.min_score_pct if crit.min_score_pct > Decimal("0.00") else self.min_individual_pct

            # Mandatory boundary condition: exactly 60% must PASS
            passed = avg_score >= min_required
            if not passed:
                all_individual_pass = False

            weight = crit.weight_pct
            weighted_contrib = quantize_percent((avg_score * weight) / Decimal("100.00"))
            weighted_sum += weighted_contrib

            res_str = "PASS" if passed else "FAIL"
            expl = (
                f"Criterion '{crit.name}' score: {avg_score}% (Evaluators: {len(crit_scores)}) satisfies minimum {min_required}%. Weighted contribution: {weighted_contrib}%."
                if passed else
                f"Criterion '{crit.name}' score: {avg_score}% fails minimum threshold of {min_required}%. Technically disqualified."
            )

            dec = DecisionRecord(
                decision_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=bid.bidder_id,
                rule_id="BR-03",
                evaluation_stage="TECHNICAL_EVALUATION",
                input_values={"criterion_code": crit.code, "raw_evaluator_scores": [str(s) for s in crit_scores], "average_score": str(avg_score)},
                required_thresholds={"min_score_pct": str(min_required), "weight_pct": str(weight)},
                calculation_details=f"Average = {avg_score}%, Weighted Contrib = ({avg_score} * {weight}%) / 100 = {weighted_contrib}%",
                result=res_str,
                human_explanation=expl,
                evidence_reference=f"Technical Evaluation Sheet - {crit.code}",
                created_at=now_iso()
            )
            decisions.append(dec)

        overall_score = quantize_percent(weighted_sum)
        # Mandatory boundary condition: exactly 70% must PASS
        overall_passed = overall_score >= self.min_overall_pct
        is_qualified = all_individual_pass and overall_passed

        overall_result = "PASS" if is_qualified else "FAIL"
        if not all_individual_pass:
            overall_expl = f"Technical disqualification: One or more individual criteria scored below {self.min_individual_pct}%, despite overall weighted score of {overall_score}%."
        elif not overall_passed:
            overall_expl = f"Technical disqualification: Overall weighted score of {overall_score}% is below the mandatory cut-off of {self.min_overall_pct}%."
        else:
            overall_expl = f"Technical qualification successful: Overall weighted score is {overall_score}%, meeting or exceeding {self.min_overall_pct}% with all individual cut-offs cleared."

        dec_overall = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            tender_id=tender.tender_id,
            bidder_id=bid.bidder_id,
            rule_id="BR-03",
            evaluation_stage="TECHNICAL_EVALUATION",
            input_values={"criterion_scores": {k: str(v) for k, v in criterion_scores.items()}, "total_weighted_score": str(overall_score)},
            required_thresholds={"min_overall_score_pct": str(self.min_overall_pct), "min_individual_pct": str(self.min_individual_pct)},
            calculation_details=f"Total Weighted Score = {overall_score}% >= {self.min_overall_pct}%: {overall_passed}, All individual >= {self.min_individual_pct}%: {all_individual_pass}",
            result=overall_result,
            human_explanation=overall_expl,
            evidence_reference="Consolidated Technical Scorecard",
            created_at=now_iso()
        )
        decisions.append(dec_overall)

        return is_qualified, overall_score, criterion_scores, decisions
