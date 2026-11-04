"""
TENDERLENS — Bid Validity Unit Tests (BR-08 / FR-10)
Tests 90-day base validity, calendar inclusivity, extension refusal with penalty-free exit, and expiry.
"""

from src.engines.validity_engine import ValidityEngine
from src.utils.date_utils import add_days


def test_validity_boundary_day_90_is_valid(configs, sample_tender, sample_bid):
    engine = ValidityEngine(configs["business_rules"])
    # Day 90 from bid opening date 2026-01-01
    day_90 = add_days(sample_tender.bid_opening_date, 90)

    is_valid, status, expiry, dec = engine.evaluate_validity(sample_tender, sample_bid, as_of_date=day_90)
    assert is_valid is True
    assert status == "VALID"
    assert dec.result == "PASS"


def test_extension_refusal_permits_clean_exit_without_forfeiture(configs, sample_tender, sample_bid):
    engine = ValidityEngine(configs["business_rules"])
    is_valid, status, expiry, dec = engine.evaluate_validity(
        sample_tender, sample_bid, extension_response="REJECTED"
    )
    # Refusal does not penalize or forfeit EMD
    assert status == "EXITED_NO_FORFEITURE"
    assert dec.result == "SKIPPED"


def test_expired_bid_validity(configs, sample_tender, sample_bid):
    engine = ValidityEngine(configs["business_rules"])
    day_91 = add_days(sample_tender.bid_opening_date, 91)

    is_valid, status, expiry, dec = engine.evaluate_validity(sample_tender, sample_bid, as_of_date=day_91)
    assert is_valid is False
    assert status == "EXPIRED"
    assert dec.result == "FAIL"
