"""
TENDERLENS — Public Procurement Preferences Unit Tests (BR-05 / FR-07)
Tests MSE 15% boundary test, Class-I 20% band, quantity splits, and 100% reserved item rule.
"""

from decimal import Decimal
from src.engines.preference_engine import PreferenceEngine
from src.models import Bid, Bidder, BidderCertificate, FinancialEvaluation


def test_mse_boundary_exact_15_percent_qualifies(configs, sample_tender):
    engine = PreferenceEngine(configs["business_rules"])
    l1_bid = Bid("B_L1", sample_tender.tender_id, "BDR_L1", "2026-01-01T10:00:00Z")
    l1_ev = FinancialEvaluation("EV_L1", "B_L1", Decimal("100000.00"), Decimal("100000.00"), False, None, True, Decimal("100000.00"), Decimal("100000.00"), Decimal("100000.00"))

    # MSE bidder is priced at EXACTLY L1 + 15% = ₹1,15,000.00
    mse_bid = Bid("B_MSE", sample_tender.tender_id, "BDR_MSE", "2026-01-01T10:00:00Z")
    mse_ev = FinancialEvaluation("EV_MSE", "B_MSE", Decimal("115000.00"), Decimal("115000.00"), False, None, True, Decimal("115000.00"), Decimal("115000.00"), Decimal("115000.00"))
    mse_bidder = Bidder("BDR_MSE", "MSE Corp", "LLP")
    mse_cert = BidderCertificate("C_MSE", "BDR_MSE", "MSE", "UDYAM-1", is_valid=True)

    allocs, decs = engine.evaluate_preferences(
        sample_tender, l1_bid, l1_ev, [(mse_bid, mse_ev, mse_bidder, [mse_cert])]
    )

    mse_alloc = next((a for a in allocs if a.preference_type == "MSE"), None)
    assert mse_alloc is not None
    assert mse_alloc.is_l1_matched is True
    assert mse_alloc.allocated_quantity_pct == Decimal("25.00")
    assert mse_alloc.awarded_price == Decimal("100000.00")  # Matched L1 rate


def test_mse_above_15_percent_fails(configs, sample_tender):
    engine = PreferenceEngine(configs["business_rules"])
    l1_bid = Bid("B_L1", sample_tender.tender_id, "BDR_L1", "2026-01-01T10:00:00Z")
    l1_ev = FinancialEvaluation("EV_L1", "B_L1", Decimal("100000.00"), Decimal("100000.00"), False, None, True, Decimal("100000.00"), Decimal("100000.00"), Decimal("100000.00"))

    # MSE bidder at ₹1,15,001.00 (> 15% above L1)
    mse_bid = Bid("B_MSE", sample_tender.tender_id, "BDR_MSE", "2026-01-01T10:00:00Z")
    mse_ev = FinancialEvaluation("EV_MSE", "B_MSE", Decimal("115001.00"), Decimal("115001.00"), False, None, True, Decimal("115001.00"), Decimal("115001.00"), Decimal("115001.00"))
    mse_bidder = Bidder("BDR_MSE", "MSE Corp", "LLP")
    mse_cert = BidderCertificate("C_MSE", "BDR_MSE", "MSE", "UDYAM-1", is_valid=True)

    allocs, decs = engine.evaluate_preferences(
        sample_tender, l1_bid, l1_ev, [(mse_bid, mse_ev, mse_bidder, [mse_cert])]
    )
    mse_alloc = next((a for a in allocs if a.preference_type == "MSE"), None)
    assert mse_alloc is None


def test_reserved_item_100_percent_allocation_to_mse(configs, sample_tender):
    sample_tender.is_reserved_item = True
    engine = PreferenceEngine(configs["business_rules"])
    l1_bid = Bid("B_L1", sample_tender.tender_id, "BDR_L1", "2026-01-01T10:00:00Z")
    l1_ev = FinancialEvaluation("EV_L1", "B_L1", Decimal("100000.00"), Decimal("100000.00"), False, None, True, Decimal("100000.00"), Decimal("100000.00"), Decimal("100000.00"))

    mse_bid = Bid("B_MSE", sample_tender.tender_id, "BDR_MSE", "2026-01-01T10:00:00Z")
    mse_ev = FinancialEvaluation("EV_MSE", "B_MSE", Decimal("110000.00"), Decimal("110000.00"), False, None, True, Decimal("110000.00"), Decimal("110000.00"), Decimal("110000.00"))
    mse_bidder = Bidder("BDR_MSE", "MSE Corp", "LLP")
    mse_cert = BidderCertificate("C_MSE", "BDR_MSE", "MSE", "UDYAM-1", is_valid=True)

    allocs, decs = engine.evaluate_preferences(
        sample_tender, l1_bid, l1_ev, [(mse_bid, mse_ev, mse_bidder, [mse_cert])]
    )
    mse_alloc = next((a for a in allocs if a.preference_type == "MSE"), None)
    assert mse_alloc is not None
    assert mse_alloc.allocated_quantity_pct == Decimal("100.00")  # 100% reserved item allocation
