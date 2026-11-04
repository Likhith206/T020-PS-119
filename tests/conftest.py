"""
TENDERLENS — Pytest Fixtures and Global Test Configuration
Provides clean in-memory databases, loaded configurations, and standardized mock entities.
"""

import pytest
from decimal import Decimal
from src.storage.database import Database
from src.utils.validators import validate_config_files
from src.models import Tender, Bidder, Bid, TechnicalCriterion, PriceScheduleItem


@pytest.fixture
def configs():
    return validate_config_files("config")


@pytest.fixture
def mem_db():
    db = Database(db_path=":memory:", schema_path="database/schema.sql")
    db.init_db()
    return db


@pytest.fixture
def sample_tender():
    return Tender(
        tender_id="TND_TEST_01",
        title="Test Infrastructure Modernization",
        description="Comprehensive cloud cluster deployment",
        estimated_cost=Decimal("10000000.00"),  # ₹1 Crore
        bid_opening_date="2026-01-01",
        bid_closing_date="2026-01-25",
        bid_validity_days=90,
        evaluation_method="LCS",
        qcbs_tech_weight=Decimal("70.00"),
        qcbs_fin_weight=Decimal("30.00"),
        emd_required=True,
        emd_amount=Decimal("200000.00"),  # 2% of 1 Crore
        mse_relax_enabled=True,
        single_bid_allowed=False,
        is_reserved_item=False,
        status="PUBLISHED",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_bidder():
    return Bidder(
        bidder_id="BDR_TEST_01",
        name="Apex Systems Pvt Ltd",
        organization_type="Private Limited",
        registration_no="REG-991122",
        pan_no="AABBA1234C",
        gstin="29AABBA1234C1Z5",
        is_blacklisted=False,
        created_at="2026-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_bid():
    return Bid(
        bid_id="BID_TEST_01",
        tender_id="TND_TEST_01",
        bidder_id="BDR_TEST_01",
        submission_timestamp="2026-01-15T10:00:00Z",
        technical_envelope_opened=False,
        financial_envelope_opened=False,
        responsiveness_status="RESPONSIVE",
        technical_status="QUALIFIED",
        overall_technical_score=Decimal("82.00"),
        financial_status="LOCKED",
        created_at="2026-01-15T10:00:00Z"
    )
