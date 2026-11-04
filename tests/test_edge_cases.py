"""
TENDERLENS — Edge Cases & Boundary Conditions Unit Tests
Tests unit-rate correction changing L1, single-bid re-tender, malformed inputs, and preference chaining.
"""

import pytest
from decimal import Decimal
from src.engines.single_bid_engine import SingleBidEngine
from src.engines.ranking_engine import RankingEngine
from src.engines.financial_engine import FinancialEngine
from src.models import Bid, FinancialEvaluation, PriceScheduleItem
from src.utils.validators import ValidationError, validate_tender_dict


def test_unit_rate_correction_changes_l1(configs, sample_tender):
    """Verifies that an arithmetic correction on unit rates can legitimately alter L1 ranking."""
    sample_tender.evaluation_method = "LCS"
    rank_engine = RankingEngine(configs["scoring_defaults"])

    # Bidder A quoted total was ₹95 Lakh, but calculated from unit rates it is actually ₹1.10 Crore
    b_a = Bid("BA", sample_tender.tender_id, "BDRA", "2026-01-01T10:00:00Z", overall_technical_score=Decimal("80.00"))
    ev_a = FinancialEvaluation("EA", "BA", Decimal("9500000.00"), Decimal("11000000.00"), True, "Corrected up", True, Decimal("11000000.00"), Decimal("11000000.00"), Decimal("11000000.00"))

    # Bidder B quoted ₹1.00 Crore without error
    b_b = Bid("BB", sample_tender.tender_id, "BDRB", "2026-01-01T10:00:00Z", overall_technical_score=Decimal("80.00"))
    ev_b = FinancialEvaluation("EB", "BB", Decimal("10000000.00"), Decimal("10000000.00"), False, None, True, Decimal("10000000.00"), Decimal("10000000.00"), Decimal("10000000.00"))

    # Before correction, A appeared lower. After correction, B (₹1.00 Cr) is strictly lower than A (₹1.10 Cr) -> B wins L1!
    ranked, decs = rank_engine.rank_bids(sample_tender, [(b_a, ev_a), (b_b, ev_b)])
    assert ranked[0][0].bid_id == "BB"
    assert ranked[0][2] == 1  # Bidder B is L1
    assert ranked[1][0].bid_id == "BA"
    assert ranked[1][2] == 2  # Bidder A is L2


def test_single_responsive_bid_retender_when_not_allowed(configs, sample_tender):
    sample_tender.single_bid_allowed = False
    engine = SingleBidEngine(configs["business_rules"])

    single_bid = [Bid("B1", sample_tender.tender_id, "BDR1", "2026-01-01T10:00:00Z")]
    can_proceed, action, dec = engine.evaluate_competition(sample_tender, single_bid)

    assert can_proceed is False
    assert action == "TRIGGER_RETENDER"
    assert dec.result == "FAIL"


def test_invalid_tender_validation():
    # Negative estimated cost must raise ValidationError
    with pytest.raises(ValidationError):
        validate_tender_dict({
            "tender_id": "TND_NEG",
            "title": "Invalid Tender",
            "estimated_cost": "-1000.00",
            "bid_opening_date": "2026-01-01",
            "bid_closing_date": "2026-01-10",
            "evaluation_method": "LCS"
        })

    # Close date before open date must raise ValidationError
    with pytest.raises(ValidationError):
        validate_tender_dict({
            "tender_id": "TND_DATE",
            "title": "Invalid Date",
            "estimated_cost": "100000.00",
            "bid_opening_date": "2026-02-01",
            "bid_closing_date": "2026-01-10",
            "evaluation_method": "LCS"
        })
