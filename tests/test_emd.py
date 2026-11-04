"""
TENDERLENS — EMD Unit Tests (BR-02 / FR-04)
Tests EMD cap, MSE/Startup exemptions, and the mandatory exactly 45-day BG validity boundary condition.
"""

from decimal import Decimal
from src.engines.emd_engine import EMDEngine
from src.models import EMDRecord, BidderCertificate
from src.utils.date_utils import add_days


def test_emd_calculation_and_cap(configs):
    engine = EMDEngine(configs["business_rules"])
    # 2% of ₹10 Crore (₹100,000,000) is ₹20 Lakh (below 50L cap)
    assert engine.calculate_required_emd(Decimal("100000000.00")) == Decimal("2000000.00")

    # 2% of ₹50 Crore (₹500,000,000) is ₹1 Crore (exceeds cap) -> capped at ₹50 Lakh
    assert engine.calculate_required_emd(Decimal("500000000.00")) == Decimal("5000000.00")


def test_emd_boundary_exactly_45_days_passes(configs, sample_tender, sample_bidder):
    engine = EMDEngine(configs["business_rules"])
    bid_validity_end = add_days(sample_tender.bid_opening_date, sample_tender.bid_validity_days)
    exact_45_days_bg = add_days(bid_validity_end, 45)

    emd = EMDRecord(
        emd_id="EMD_B1",
        tender_id=sample_tender.tender_id,
        bidder_id=sample_bidder.bidder_id,
        payment_mode="BG",
        amount_paid=sample_tender.emd_amount,
        valid_until=exact_45_days_bg,
        instrument_reference="BG-EXACT-45"
    )

    is_valid, status, dec = engine.evaluate(sample_tender, sample_bidder, emd, certificates=[])
    assert is_valid is True
    assert status == "VALID"
    assert dec.result == "PASS"


def test_emd_less_than_45_days_fails(configs, sample_tender, sample_bidder):
    engine = EMDEngine(configs["business_rules"])
    bid_validity_end = add_days(sample_tender.bid_opening_date, sample_tender.bid_validity_days)
    short_bg = add_days(bid_validity_end, 44)  # 44 days < 45 days

    emd = EMDRecord(
        emd_id="EMD_B2",
        tender_id=sample_tender.tender_id,
        bidder_id=sample_bidder.bidder_id,
        payment_mode="BG",
        amount_paid=sample_tender.emd_amount,
        valid_until=short_bg,
        instrument_reference="BG-SHORT-44"
    )

    is_valid, status, dec = engine.evaluate(sample_tender, sample_bidder, emd, certificates=[])
    assert is_valid is False
    assert status == "INVALID"
    assert dec.result == "FAIL"


def test_emd_mse_and_startup_exemption(configs, sample_tender, sample_bidder):
    engine = EMDEngine(configs["business_rules"])
    emd = EMDRecord(
        emd_id="EMD_B3",
        tender_id=sample_tender.tender_id,
        bidder_id=sample_bidder.bidder_id,
        exemption_claimed=True,
        exemption_category="MSE"
    )
    cert = BidderCertificate(
        cert_id="CERT_MSE",
        bidder_id=sample_bidder.bidder_id,
        cert_type="MSE",
        registration_number="UDYAM-01",
        is_valid=True
    )

    is_valid, status, dec = engine.evaluate(sample_tender, sample_bidder, emd, certificates=[cert])
    assert is_valid is True
    assert status == "VALID"
    assert dec.result == "PASS"


def test_emd_insufficient_payment_fails(configs, sample_tender, sample_bidder):
    engine = EMDEngine(configs["business_rules"])
    emd = EMDRecord(
        emd_id="EMD_B4",
        tender_id=sample_tender.tender_id,
        bidder_id=sample_bidder.bidder_id,
        payment_mode="ONLINE",
        amount_paid=Decimal("150000.00")  # ₹1.5L < ₹2.0L required
    )

    is_valid, status, dec = engine.evaluate(sample_tender, sample_bidder, emd, certificates=[])
    assert is_valid is False
    assert status == "INVALID"
    assert dec.result == "FAIL"
