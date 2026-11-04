"""
TENDERLENS — Ranking Unit Tests (BR-06 / FR-08)
Tests Least Cost Selection (LCS), QCBS inverse proportional scoring, and tie-breakers.
"""

from decimal import Decimal
from src.engines.ranking_engine import RankingEngine
from src.models import Bid, FinancialEvaluation


def test_lcs_ranking_and_tie_breaker(configs, sample_tender):
    sample_tender.evaluation_method = "LCS"
    engine = RankingEngine(configs["scoring_defaults"])

    # Bid 1: ₹50,00,000, Tech 80%
    b1 = Bid("B1", sample_tender.tender_id, "BDR1", "2026-01-01T10:00:00Z")
    b1.overall_technical_score = Decimal("80.00")
    ev1 = FinancialEvaluation("E1", "B1", Decimal("5000000.00"), Decimal("5000000.00"), False, None, True, Decimal("5000000.00"), Decimal("5000000.00"), Decimal("5000000.00"))

    # Bid 2: ₹48,00,000, Tech 75% -> Lower price wins L1
    b2 = Bid("B2", sample_tender.tender_id, "BDR2", "2026-01-01T10:00:00Z")
    b2.overall_technical_score = Decimal("75.00")
    ev2 = FinancialEvaluation("E2", "B2", Decimal("4800000.00"), Decimal("4800000.00"), False, None, True, Decimal("4800000.00"), Decimal("4800000.00"), Decimal("4800000.00"))

    ranked, decs = engine.rank_bids(sample_tender, [(b1, ev1), (b2, ev2)])
    assert ranked[0][0].bid_id == "B2"
    assert ranked[0][2] == 1  # Rank 1
    assert ranked[1][0].bid_id == "B1"
    assert ranked[1][2] == 2  # Rank 2


def test_qcbs_scoring_and_ranking(configs, sample_tender):
    sample_tender.evaluation_method = "QCBS"
    sample_tender.qcbs_tech_weight = Decimal("70.00")
    sample_tender.qcbs_fin_weight = Decimal("30.00")
    engine = RankingEngine(configs["scoring_defaults"])

    # Bid 1: High Tech (90%), High Price (₹100,000)
    b1 = Bid("B1", sample_tender.tender_id, "BDR1", "2026-01-01T10:00:00Z")
    b1.overall_technical_score = Decimal("90.00")
    ev1 = FinancialEvaluation("E1", "B1", Decimal("100000.00"), Decimal("100000.00"), False, None, True, Decimal("100000.00"), Decimal("100000.00"), Decimal("100000.00"))

    # Bid 2: Lower Tech (75%), Lowest Price L1 (₹80,000) -> Fin score = 100.00
    b2 = Bid("B2", sample_tender.tender_id, "BDR2", "2026-01-01T10:00:00Z")
    b2.overall_technical_score = Decimal("75.00")
    ev2 = FinancialEvaluation("E2", "B2", Decimal("80000.00"), Decimal("80000.00"), False, None, True, Decimal("80000.00"), Decimal("80000.00"), Decimal("80000.00"))

    ranked, decs = engine.rank_bids(sample_tender, [(b1, ev1), (b2, ev2)])

    # B2 Fin Score = (80000/80000)*100 = 100.00 -> Composite = (75*0.7) + (100*0.3) = 52.5 + 30 = 82.50
    # B1 Fin Score = (80000/100000)*100 = 80.00 -> Composite = (90*0.7) + (80*0.3) = 63.0 + 24 = 87.00
    # B1 has higher composite score (87.00 > 82.50) -> B1 is Rank 1!
    assert ranked[0][0].bid_id == "B1"
    assert ranked[0][2] == 1
    assert ranked[0][1].combined_qcbs_score == Decimal("87.00")
