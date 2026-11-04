"""
TENDERLENS — Audit Ledger Unit Tests
Tests SHA-256 hash linking, genesis anchoring, and cryptographic detection of modified or deleted events.
"""

from src.intelligence.audit_engine import AuditEngine
from src.storage.repositories import TenderRepository


def test_audit_hash_chain_validity(mem_db, sample_tender):
    TenderRepository(mem_db).save(sample_tender)
    audit = AuditEngine(mem_db)

    # Log 3 sequential events
    audit.log_event(sample_tender.tender_id, "TENDER_PUBLISHED", {"cost": "10000000.00"})
    audit.log_event(sample_tender.tender_id, "BID_REGISTERED", {"bidder": "BDR001"})
    audit.log_event(sample_tender.tender_id, "EMD_VERIFIED", {"status": "VALID"})

    is_valid, findings = audit.verify_chain(sample_tender.tender_id)
    assert is_valid is True
    assert "Audit chain completely verified" in findings[0]


def test_audit_detects_data_tampering(mem_db, sample_tender):
    TenderRepository(mem_db).save(sample_tender)
    audit = AuditEngine(mem_db)

    audit.log_event(sample_tender.tender_id, "TENDER_PUBLISHED", {"cost": "10000000.00"})
    audit.log_event(sample_tender.tender_id, "BID_REGISTERED", {"bidder": "BDR001"})

    # Maliciously modify event details in SQLite
    mem_db.execute_query(
        "UPDATE audit_events SET event_details = '{\"bidder\": \"MALICIOUS_BIDDER\"}' WHERE sequence_no = 2"
    )

    is_valid, findings = audit.verify_chain(sample_tender.tender_id)
    assert is_valid is False
    assert any("Cryptographic Tampering Detected" in f for f in findings)


def test_audit_detects_deleted_event(mem_db, sample_tender):
    TenderRepository(mem_db).save(sample_tender)
    audit = AuditEngine(mem_db)

    audit.log_event(sample_tender.tender_id, "E1", {})
    audit.log_event(sample_tender.tender_id, "E2", {})
    audit.log_event(sample_tender.tender_id, "E3", {})

    # Maliciously delete sequence 2
    mem_db.execute_query("DELETE FROM audit_events WHERE sequence_no = 2")

    is_valid, findings = audit.verify_chain(sample_tender.tender_id)
    assert is_valid is False
    assert any("Sequence Integrity Violation" in f or "Hash Chain Discontinuity" in f for f in findings)
