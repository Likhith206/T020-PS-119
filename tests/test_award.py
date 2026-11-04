"""
TENDERLENS — Award and Security Unit Tests (BR-09, BR-11 / FR-11, FR-13)
Tests LoA generation, standard 3% vs abnormal 5% security, 21-day default handling, and L1-only negotiation.
"""

from decimal import Decimal
from src.engines.award_engine import AwardEngine
from src.engines.negotiation_engine import NegotiationEngine
from src.models import Bid, FinancialEvaluation


def test_award_standard_performance_security(configs, sample_tender, sample_bid):
    engine = AwardEngine(configs["business_rules"])
    ev = FinancialEvaluation("E1", sample_bid.bid_id, Decimal("10000000.00"), Decimal("10000000.00"), False, None, True, Decimal("10000000.00"), Decimal("10000000.00"), Decimal("10000000.00"), is_abnormally_low=False)

    award, sec, dec = engine.create_award(sample_tender, sample_bid, ev, loa_date="2026-02-01")
    # Standard security is 3% of ₹1 Crore = ₹3,00,000.00
    assert sec.standard_security_rate_pct == Decimal("3.00")
    assert sec.total_security_required == Decimal("300000.00")
    assert award.security_due_date == "2026-02-22"  # 21 days from 2026-02-01


def test_award_abnormal_performance_security(configs, sample_tender, sample_bid):
    engine = AwardEngine(configs["business_rules"])
    ev = FinancialEvaluation(
        "E1", sample_bid.bid_id, Decimal("7000000.00"), Decimal("7000000.00"),
        False, None, True, Decimal("7000000.00"), Decimal("7000000.00"), Decimal("7000000.00"),
        is_abnormally_low=True, additional_security_required=Decimal("500000.00")
    )

    award, sec, dec = engine.create_award(sample_tender, sample_bid, ev, loa_date="2026-02-01")
    # Abnormal base security is 5% of ₹70 Lakh (₹3,50,000) + Additional ₹5,00,000 = ₹8,50,000.00
    assert sec.standard_security_rate_pct == Decimal("5.00")
    assert sec.total_security_required == Decimal("850000.00")


def test_awardee_default_and_next_bidder_within_10_percent(configs, sample_tender, sample_bid):
    engine = AwardEngine(configs["business_rules"])
    award, sec, _ = engine.create_award(
        sample_tender, sample_bid,
        FinancialEvaluation("E1", sample_bid.bid_id, Decimal("10000000.00"), Decimal("10000000.00"), False, None, True, Decimal("10000000.00"), Decimal("10000000.00"), Decimal("10000000.00"))
    )

    # L2 bid is ₹1,08,00,000 (within 10% of ₹1,00,00,000 = ₹1,10,00,000 cutoff)
    l2_bid = Bid("B_L2", sample_tender.tender_id, "BDR_L2", "2026-01-01T10:00:00Z")
    l2_ev = FinancialEvaluation("E_L2", "B_L2", Decimal("10800000.00"), Decimal("10800000.00"), False, None, True, Decimal("10800000.00"), Decimal("10800000.00"), Decimal("10800000.00"))

    action, expl, dec = engine.process_security_default(sample_tender, award, Decimal("10000000.00"), l2_bid, l2_ev)
    assert action == "OFFER_TO_NEXT_BIDDER"


def test_negotiation_permitted_only_with_l1_exceeding_10_percent(configs, sample_tender, sample_bid):
    engine = NegotiationEngine(configs["business_rules"])
    # Tender estimated cost: ₹1 Crore (₹10,000,000)
    # L1 quoted at ₹1,15,00,000 (exceeds estimate by 15% > 10% cutoff)
    ev_high = FinancialEvaluation("E1", sample_bid.bid_id, Decimal("11500000.00"), Decimal("11500000.00"), False, None, True, Decimal("11500000.00"), Decimal("11500000.00"), Decimal("11500000.00"))

    is_permitted, action, price, dec = engine.evaluate_negotiation_eligibility(
        sample_tender, sample_bid, ev_high, is_l1=True
    )
    assert is_permitted is True
    assert action == "NEGOTIATION_RECOMMENDED"

    # Negotiation with non-L1 is prohibited
    is_permitted_non_l1, action_non_l1, _, dec_non_l1 = engine.evaluate_negotiation_eligibility(
        sample_tender, sample_bid, ev_high, is_l1=False
    )
    assert is_permitted_non_l1 is False
    assert action_non_l1 == "NON_L1_NEGOTIATION_PROHIBITED"
