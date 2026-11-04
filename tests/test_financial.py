"""
TENDERLENS — Financial Evaluation Unit Tests (BR-04 / FR-06)
Tests strict two-envelope logical isolation, unit-rate arithmetic corrections, and tax/freight normalization.
"""

import pytest
from decimal import Decimal
from src.engines.financial_engine import FinancialEngine, TwoEnvelopeViolationError
from src.models import PriceScheduleItem


def test_two_envelope_security_enforcement(configs, sample_tender, sample_bid):
    engine = FinancialEngine(configs["business_rules"])

    # Disqualified bid must block financial envelope opening
    sample_bid.technical_status = "DISQUALIFIED"
    with pytest.raises(TwoEnvelopeViolationError):
        engine.evaluate(sample_tender, sample_bid, schedule_items=[])

    # Non-responsive bid must block financial envelope opening
    sample_bid.technical_status = "QUALIFIED"
    sample_bid.responsiveness_status = "NON_RESPONSIVE"
    with pytest.raises(TwoEnvelopeViolationError):
        engine.evaluate(sample_tender, sample_bid, schedule_items=[])


def test_arithmetic_correction_unit_rate_over_total(configs, sample_tender, sample_bid):
    engine = FinancialEngine(configs["business_rules"])
    sample_bid.responsiveness_status = "RESPONSIVE"
    sample_bid.technical_status = "QUALIFIED"

    # Bidder quotes 10 units @ ₹10,000 = ₹1,00,000, but mistakenly writes quoted total as ₹90,000
    item = PriceScheduleItem(
        schedule_id="PS_1",
        bid_id=sample_bid.bid_id,
        item_no=1,
        description="Core Router",
        quantity=Decimal("10.00"),
        unit="Nos",
        quoted_unit_rate=Decimal("10000.00"),
        quoted_total_amount=Decimal("90000.00"),
        is_gst_included=True,
        is_freight_included=True
    )

    ev, decs = engine.evaluate(sample_tender, sample_bid, [item], correction_accepted=True)
    assert ev.has_arithmetic_discrepancy is True
    assert ev.original_quoted_total == Decimal("90000.00")
    assert ev.arithmetic_corrected_total == Decimal("100000.00")
    assert ev.final_comparative_price == Decimal("100000.00")


def test_gst_and_freight_normalization(configs, sample_tender, sample_bid):
    engine = FinancialEngine(configs["business_rules"])
    sample_bid.responsiveness_status = "RESPONSIVE"
    sample_bid.technical_status = "QUALIFIED"

    # 10 units @ ₹10,000 = ₹1,00,000. GST is EXCLUDED (18%), Freight is EXCLUDED (₹5,000)
    item = PriceScheduleItem(
        schedule_id="PS_2",
        bid_id=sample_bid.bid_id,
        item_no=1,
        description="Switch Cluster",
        quantity=Decimal("10.00"),
        unit="Nos",
        quoted_unit_rate=Decimal("10000.00"),
        quoted_total_amount=Decimal("100000.00"),
        is_gst_included=False,
        gst_rate_pct=Decimal("18.00"),
        is_freight_included=False,
        freight_amount=Decimal("5000.00")
    )

    ev, decs = engine.evaluate(sample_tender, sample_bid, [item])
    # Expected: Base (100,000) + 18% GST (18,000) = 118,000 + Freight (5,000) = ₹1,23,000.00
    assert ev.base_tax_adjusted_total == Decimal("118000.00")
    assert ev.final_comparative_price == Decimal("123000.00")
