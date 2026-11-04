"""
TENDERLENS — Abnormally Low Bid Unit Tests (BR-07 / FR-09)
Tests strict inequality boundary condition (exact 85% does NOT trigger), justification rejection,
and shortfall additional security computation.
"""

from decimal import Decimal
from src.engines.abnormal_bid_engine import AbnormalBidEngine
from src.models import FinancialEvaluation


def test_abnormal_boundary_exact_85_percent_does_not_trigger(configs, sample_tender, sample_bid):
    engine = AbnormalBidEngine(configs["business_rules"])
    # Estimate is ₹1 Crore (₹10,000,000.00). Exactly 85% is ₹85,00,000.00
    exact_85_pct = Decimal("8500000.00")

    ev = FinancialEvaluation("E1", sample_bid.bid_id, exact_85_pct, exact_85_pct, False, None, True, exact_85_pct, exact_85_pct, exact_85_pct)
    # Assume average of qualified bids is ₹90,00,000 (80% of avg is ₹72,00,000; 85L > 72L)
    ev_peer = FinancialEvaluation("E2", "B_PEER", Decimal("9500000.00"), Decimal("9500000.00"), False, None, True, Decimal("9500000.00"), Decimal("9500000.00"), Decimal("9500000.00"))

    is_abnormal, is_accepted, add_sec, dec = engine.analyze_bid(
        sample_tender, sample_bid, ev, [ev, ev_peer], justification_status="ACCEPTED"
    )
    # Mandatory boundary: Exactly 85% does NOT trigger first condition!
    assert is_abnormal is False
    assert is_accepted is True
    assert add_sec == Decimal("0.00")
    assert dec.result == "PASS"


def test_abnormal_below_85_percent_triggers_flag(configs, sample_tender, sample_bid):
    engine = AbnormalBidEngine(configs["business_rules"])
    # ₹84,99,999.00 < ₹85,00,000.00 -> Triggers abnormal flag!
    below_85_pct = Decimal("8499999.00")

    ev = FinancialEvaluation("E1", sample_bid.bid_id, below_85_pct, below_85_pct, False, None, True, below_85_pct, below_85_pct, below_85_pct)
    ev_peer = FinancialEvaluation("E2", "B_PEER", Decimal("9500000.00"), Decimal("9500000.00"), False, None, True, Decimal("9500000.00"), Decimal("9500000.00"), Decimal("9500000.00"))

    # When justification is rejected -> bid is rejected
    is_abnormal, is_accepted, add_sec, dec = engine.analyze_bid(
        sample_tender, sample_bid, ev, [ev, ev_peer], justification_status="REJECTED"
    )
    assert is_abnormal is True
    assert is_accepted is False
    assert dec.result == "FAIL"

    # When justification is accepted -> bid accepted with additional security
    is_abnormal, is_accepted, add_sec, dec = engine.analyze_bid(
        sample_tender, sample_bid, ev, [ev, ev_peer], justification_status="ACCEPTED"
    )
    assert is_abnormal is True
    assert is_accepted is True
    assert dec.result == "WARNING"
    assert add_sec >= Decimal("0.00")
