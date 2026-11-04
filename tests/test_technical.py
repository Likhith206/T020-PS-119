"""
TENDERLENS — Technical Evaluation Unit Tests (BR-03 / FR-05)
Tests individual (exact 60%) and overall (exact 70%) cut-off boundary conditions and two-envelope isolation.
"""

from decimal import Decimal
from src.engines.technical_engine import TechnicalEngine
from src.models import TechnicalCriterion, TechnicalScore


def test_technical_boundary_exact_60_individual_and_70_overall_passes(configs, sample_tender, sample_bid):
    engine = TechnicalEngine(configs["business_rules"])
    # Criteria: C1 (50% weight), C2 (50% weight)
    crit1 = TechnicalCriterion("C1", sample_tender.tender_id, "CRIT_1", "Crit 1", Decimal("50.00"), Decimal("60.00"))
    crit2 = TechnicalCriterion("C2", sample_tender.tender_id, "CRIT_2", "Crit 2", Decimal("50.00"), Decimal("60.00"))

    # Exactly 60% on C1, exactly 80% on C2 -> Overall = (60*0.5) + (80*0.5) = exactly 70.00%
    score1 = TechnicalScore("S1", sample_bid.bid_id, "C1", "EV1", Decimal("60.00"))
    score2 = TechnicalScore("S2", sample_bid.bid_id, "C2", "EV1", Decimal("80.00"))

    is_qualified, overall, crit_dict, decs = engine.evaluate(
        sample_tender, sample_bid, [crit1, crit2], [score1, score2]
    )
    assert is_qualified is True
    assert overall == Decimal("70.00")
    assert crit_dict["CRIT_1"] == Decimal("60.00")
    assert decs[-1].result == "PASS"


def test_individual_criterion_below_60_fails_even_if_overall_above_70(configs, sample_tender, sample_bid):
    engine = TechnicalEngine(configs["business_rules"])
    crit1 = TechnicalCriterion("C1", sample_tender.tender_id, "CRIT_1", "Crit 1", Decimal("30.00"), Decimal("60.00"))
    crit2 = TechnicalCriterion("C2", sample_tender.tender_id, "CRIT_2", "Crit 2", Decimal("70.00"), Decimal("60.00"))

    # C1 is 59.00% (< 60%), C2 is 90.00% -> Weighted = (59*0.3) + (90*0.7) = 17.7 + 63 = 80.7% (Overall > 70%)
    score1 = TechnicalScore("S1", sample_bid.bid_id, "C1", "EV1", Decimal("59.00"))
    score2 = TechnicalScore("S2", sample_bid.bid_id, "C2", "EV1", Decimal("90.00"))

    is_qualified, overall, crit_dict, decs = engine.evaluate(
        sample_tender, sample_bid, [crit1, crit2], [score1, score2]
    )
    assert is_qualified is False
    assert overall == Decimal("80.70")
    assert decs[-1].result == "FAIL"


def test_overall_below_70_fails(configs, sample_tender, sample_bid):
    engine = TechnicalEngine(configs["business_rules"])
    crit1 = TechnicalCriterion("C1", sample_tender.tender_id, "CRIT_1", "Crit 1", Decimal("50.00"), Decimal("60.00"))
    crit2 = TechnicalCriterion("C2", sample_tender.tender_id, "CRIT_2", "Crit 2", Decimal("50.00"), Decimal("60.00"))

    # Both are 65% (>= 60%), but overall = 65% (< 70% cutoff)
    score1 = TechnicalScore("S1", sample_bid.bid_id, "C1", "EV1", Decimal("65.00"))
    score2 = TechnicalScore("S2", sample_bid.bid_id, "C2", "EV1", Decimal("65.00"))

    is_qualified, overall, crit_dict, decs = engine.evaluate(
        sample_tender, sample_bid, [crit1, crit2], [score1, score2]
    )
    assert is_qualified is False
    assert overall == Decimal("65.00")
    assert decs[-1].result == "FAIL"
