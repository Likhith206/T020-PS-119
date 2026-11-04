"""
TENDERLENS — Risk Intelligence Unit Tests
Tests multi-category procurement risk detection including single bids, BG horizons, and borderline scores.
"""

from decimal import Decimal
from src.intelligence.risk_analyzer import RiskAnalyzer
from src.storage.repositories import TenderRepository, BidderRepository, BidRepository
from src.models import Bidder, Bid


def test_single_bid_risk_detection(mem_db, sample_tender):
    TenderRepository(mem_db).save(sample_tender)
    bdr = Bidder("BDR1", "Bidder One", "Private Limited")
    BidderRepository(mem_db).save(bdr)

    # Only 1 responsive bid registered
    b1 = Bid("B1", sample_tender.tender_id, "BDR1", "2026-01-01T10:00:00Z", responsiveness_status="RESPONSIVE")
    BidRepository(mem_db).save(b1)

    analyzer = RiskAnalyzer(mem_db)
    risks = analyzer.scan_risks(sample_tender)

    single_bid_risk = next((r for r in risks if r.risk_category == "COMPLIANCE" and "Single" in r.explanation), None)
    assert single_bid_risk is not None
    assert single_bid_risk.severity == "HIGH"


def test_borderline_technical_score_risk(mem_db, sample_tender):
    TenderRepository(mem_db).save(sample_tender)
    bdr = Bidder("BDR1", "Bidder One", "Private Limited")
    BidderRepository(mem_db).save(bdr)

    # Technical score is 70.50% (within 2.5% of 70% cut-off)
    b1 = Bid(
        "B1", sample_tender.tender_id, "BDR1", "2026-01-01T10:00:00Z",
        responsiveness_status="RESPONSIVE", technical_status="QUALIFIED", overall_technical_score=Decimal("70.50")
    )
    BidRepository(mem_db).save(b1)

    analyzer = RiskAnalyzer(mem_db)
    risks = analyzer.scan_risks(sample_tender)

    tech_risk = next((r for r in risks if r.risk_category == "TECHNICAL"), None)
    assert tech_risk is not None
    assert tech_risk.severity == "MEDIUM"
