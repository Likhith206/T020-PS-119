"""
TENDERLENS — Full End-to-End Integration Tests
Tests complete pipeline execution on synthetic tender datasets, decision graph generation,
hash-linked audit integrity, and reporting output.
"""

from src.core.evaluator import ProcurementEvaluator
from src.managers.tender_manager import TenderManager
from src.managers.bidder_manager import BidderManager
from src.utils.csv_importer import CSVImporter
from src.reporting.report_generator import ReportGenerator
from src.intelligence.audit_engine import AuditEngine


def test_full_end_to_end_pipeline(mem_db):
    t_mgr = TenderManager(mem_db)
    b_mgr = BidderManager(mem_db)

    # 1. Import Tender
    tenders = CSVImporter.import_tenders("data/input/tenders.csv")
    t1 = next(t for t in tenders if t.tender_id == "TND001")
    t_mgr.create_tender(t1)

    # 2. Import Bids and companion documents
    bids_data = CSVImporter.import_bids("data/input/bids.csv", tender_id="TND001")
    for item in bids_data:
        b_mgr.register_bidder(item["bidder"])
        b_mgr.register_bid(item["bid"])

    exps = CSVImporter.import_experience("data/input/experience.csv")
    for e in exps:
        b_mgr.add_experience(e)

    certs = CSVImporter.import_certificates("data/input/certificates.csv")
    for c in certs:
        b_mgr.add_certificate(c)

    emds = CSVImporter.import_emd_records("data/input/emd.csv", tender_id="TND001")
    for emd in emds:
        b_mgr.save_emd(emd)

    scheds = CSVImporter.import_price_schedules("data/input/price_schedules.csv")
    for s in scheds:
        if s.bid_id.startswith("BID_T1_"):
            b_mgr.save_price_schedule_item(s)

    scores = CSVImporter.import_technical_scores("data/input/technical_scores.csv")
    from src.models import TechnicalScore
    from src.utils.date_utils import now_iso
    for s in scores:
        if s["bid_id"].startswith("BID_T1_"):
            crit_id = f"TND001_{s['criterion_code']}"
            sc = TechnicalScore(s["score_id"], s["bid_id"], crit_id, s["evaluator_id"], s["raw_score"], s["remarks"], now_iso())
            b_mgr.save_technical_score(sc)

    # 3. Execute master evaluator
    evaluator = ProcurementEvaluator(mem_db)
    res = evaluator.evaluate_tender("TND001")

    assert res["status"] == "AWARDED"
    assert res["award"] is not None
    assert res["award"].awarded_bidder_id == "BDR007"
    assert res["performance_security"] is not None

    # 4. Verify audit ledger chain
    audit = AuditEngine(mem_db)
    is_valid, findings = audit.verify_chain("TND001")
    assert is_valid is True
    assert "completely verified" in findings[0]

    # 5. Verify full report dossier generation
    reporter = ReportGenerator(mem_db)
    text_report = reporter.generate_full_report("TND001")
    assert "TENDERLENS — CONSOLIDATED PROCUREMENT EVALUATION REPORT" in text_report
    assert "BDR007" in text_report
    assert "VERIFIED (100% Intact SHA-256 Linkage)" in text_report
