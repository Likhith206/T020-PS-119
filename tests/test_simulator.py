"""
TENDERLENS — Simulation Engine Unit Tests
Tests complete logical isolation of What-If simulation from official tender records and audit ledgers.
"""

from decimal import Decimal
from src.intelligence.simulator import SimulationEngine
from src.storage.repositories import TenderRepository, BidderRepository, BidRepository, AwardRepository
from src.models import Bidder, Bid, Award


def test_simulation_complete_isolation(mem_db, sample_tender):
    TenderRepository(mem_db).save(sample_tender)
    bdr1 = Bidder("BDR1", "Bidder One", "Private Limited")
    bdr2 = Bidder("BDR2", "Bidder Two", "Private Limited")
    BidderRepository(mem_db).save(bdr1)
    BidderRepository(mem_db).save(bdr2)

    b1 = Bid("B1", sample_tender.tender_id, "BDR1", "2026-01-01T10:00:00Z", responsiveness_status="RESPONSIVE", final_rank=1)
    b2 = Bid("B2", sample_tender.tender_id, "BDR2", "2026-01-01T10:00:00Z", responsiveness_status="RESPONSIVE", final_rank=2)
    BidRepository(mem_db).save(b1)
    BidRepository(mem_db).save(b2)

    award = Award("AWD_1", sample_tender.tender_id, "BDR1", Decimal("5000000.00"), "LCS", "LOA/01", "2026-02-01", "2026-02-22", "LOA_ISSUED", "2026-02-01T00:00:00Z")
    AwardRepository(mem_db).save_award(award)

    sim = SimulationEngine(mem_db)
    res = sim.run_simulation(sample_tender.tender_id, scenario="l1_withdrawal")

    assert res["simulation_id"].startswith("SIM_L1_WITHDRAWAL_")
    assert "withdrew" in res["diff_summary"][0]

    # Verify official record is 100% untouched
    official_award = AwardRepository(mem_db).get_by_tender(sample_tender.tender_id)
    assert official_award.awarded_bidder_id == "BDR1"
    assert official_award.status == "LOA_ISSUED"

    official_b1 = BidRepository(mem_db).get_by_id("B1")
    assert official_b1.responsiveness_status == "RESPONSIVE"  # NOT marked WITHDRAWN in official db
