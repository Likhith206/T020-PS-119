"""
TENDERLENS — Eligibility Unit Tests (BR-01 / FR-03)
Tests turnover cutoffs (exact 30% boundary test), experience options, blacklisting, and MSE relaxation.
"""

from decimal import Decimal
from src.engines.eligibility_engine import EligibilityEngine
from src.models import BidderExperience, BidderCertificate


def test_turnover_boundary_exactly_30_percent_passes(configs, sample_tender, sample_bidder):
    engine = EligibilityEngine(configs["business_rules"])
    # Estimated cost is ₹1 Crore. Exactly 30% is ₹30,00,000.00
    exact_30_pct = Decimal("3000000.00")

    # Satisfy experience via 1 work >= 80% (₹80 Lakh)
    exp = [BidderExperience(
        exp_id="EXP_1",
        bidder_id=sample_bidder.bidder_id,
        client_name="Test Client",
        project_title="Cloud Cluster",
        completion_date="2024-01-01",
        contract_value=Decimal("8500000.00")
    )]

    is_eligible, code, decs = engine.evaluate(
        sample_tender, sample_bidder, avg_turnover=exact_30_pct, experiences=exp, certificates=[]
    )
    assert is_eligible is True
    assert code == "QUALIFIED"
    assert decs[-2].result == "PASS"


def test_turnover_below_30_percent_fails(configs, sample_tender, sample_bidder):
    engine = EligibilityEngine(configs["business_rules"])
    below_30_pct = Decimal("2999999.00")  # Less than 30%

    exp = [BidderExperience(
        exp_id="EXP_1",
        bidder_id=sample_bidder.bidder_id,
        client_name="Test Client",
        project_title="Cloud Cluster",
        completion_date="2024-01-01",
        contract_value=Decimal("8500000.00")
    )]

    is_eligible, code, decs = engine.evaluate(
        sample_tender, sample_bidder, avg_turnover=below_30_pct, experiences=exp, certificates=[]
    )
    assert is_eligible is False
    assert code == "TURNOVER_INSUFFICIENT"


def test_experience_options_80_50_40(configs, sample_tender, sample_bidder):
    engine = EligibilityEngine(configs["business_rules"])
    turnover = Decimal("5000000.00")

    # Option 2: 2 works >= 50% each (₹50 Lakh each on ₹1 Crore tender)
    exp_opt2 = [
        BidderExperience("E1", sample_bidder.bidder_id, "C1", "P1", "2023-01-01", Decimal("5200000.00")),
        BidderExperience("E2", sample_bidder.bidder_id, "C2", "P2", "2024-01-01", Decimal("5100000.00"))
    ]
    is_eligible, code, decs = engine.evaluate(sample_tender, sample_bidder, turnover, exp_opt2, [])
    assert is_eligible is True
    assert code == "QUALIFIED"

    # Option 3: 3 works >= 40% each (₹40 Lakh each)
    exp_opt3 = [
        BidderExperience("E3", sample_bidder.bidder_id, "C1", "P1", "2023-01-01", Decimal("4100000.00")),
        BidderExperience("E4", sample_bidder.bidder_id, "C2", "P2", "2024-01-01", Decimal("4200000.00")),
        BidderExperience("E5", sample_bidder.bidder_id, "C3", "P3", "2025-01-01", Decimal("4000000.00"))
    ]
    is_eligible, code, decs = engine.evaluate(sample_tender, sample_bidder, turnover, exp_opt3, [])
    assert is_eligible is True
    assert code == "QUALIFIED"


def test_blacklisted_bidder_disqualified(configs, sample_tender, sample_bidder):
    engine = EligibilityEngine(configs["business_rules"])
    sample_bidder.is_blacklisted = True
    sample_bidder.blacklisted_since = "2025-06-01"

    is_eligible, code, decs = engine.evaluate(
        sample_tender, sample_bidder, avg_turnover=Decimal("50000000.00"), experiences=[], certificates=[]
    )
    assert is_eligible is False
    assert code == "BLACKLISTED"
    assert decs[0].result == "FAIL"


def test_mse_relaxation_waives_turnover_and_experience(configs, sample_tender, sample_bidder):
    engine = EligibilityEngine(configs["business_rules"])
    sample_tender.mse_relax_enabled = True
    cert = BidderCertificate("CERT_MSE", sample_bidder.bidder_id, "MSE", "UDYAM-99", is_valid=True)

    # 0 turnover and 0 experience passes when MSE relaxation is active
    is_eligible, code, decs = engine.evaluate(
        sample_tender, sample_bidder, avg_turnover=Decimal("0.00"), experiences=[], certificates=[cert]
    )
    assert is_eligible is True
    assert code == "QUALIFIED_MSE_RELAXED"
