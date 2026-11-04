"""
TENDERLENS — Tamper-Evident Audit Ledger (Intelligence Subsystem)
Constructs a cryptographically chained, hash-linked ledger of all procurement events using SHA-256.
Provides mathematical audit verification, detecting modified, deleted, or re-ordered events.
"""

import json
import hashlib
import uuid
from typing import List, Dict, Any, Tuple, Optional
from src.models import AuditEvent
from src.storage.database import Database
from src.storage.repositories import AuditRepository
from src.utils.date_utils import now_iso


class AuditVerificationError(Exception):
    """Raised when the audit chain integrity check fails."""
    pass


class AuditEngine:
    def __init__(self, db: Database, genesis_hash: str = "0000000000000000000000000000000000000000000000000000000000000000"):
        self.db = db
        self.repo = AuditRepository(db)
        self.genesis_hash = genesis_hash

    def log_event(
        self,
        tender_id: str,
        event_type: str,
        event_details: Dict[str, Any],
        bidder_id: Optional[str] = None
    ) -> AuditEvent:
        """Appends a new hash-linked event to the tender's audit chain."""
        last_event = self.repo.get_last_event(tender_id)

        if last_event is None:
            sequence_no = 1
            prev_hash = self.genesis_hash
        else:
            sequence_no = last_event.sequence_no + 1
            prev_hash = last_event.current_hash

        event_id = str(uuid.uuid4())
        timestamp = now_iso()

        # Canonical representation for deterministic hashing
        canonical_payload = json.dumps({
            "event_id": event_id,
            "tender_id": tender_id,
            "bidder_id": bidder_id,
            "sequence_no": sequence_no,
            "event_type": event_type,
            "details": event_details,
            "timestamp": timestamp
        }, sort_keys=True)

        # Hash: SHA256(prev_hash + canonical_payload)
        hash_input = (prev_hash + canonical_payload).encode("utf-8")
        current_hash = hashlib.sha256(hash_input).hexdigest()

        event = AuditEvent(
            event_id=event_id,
            tender_id=tender_id,
            bidder_id=bidder_id,
            sequence_no=sequence_no,
            event_type=event_type,
            event_details=event_details,
            previous_hash=prev_hash,
            current_hash=current_hash,
            timestamp=timestamp
        )

        self.repo.save(event)
        return event

    def verify_chain(self, tender_id: str) -> Tuple[bool, List[str]]:
        """
        Walks the audit chain sequentially from sequence 1, re-computing each SHA-256 hash.
        Detects tampering, deletions, re-ordering, and corrupted links.
        Returns: (is_valid, list_of_findings)
        """
        events = self.repo.list_by_tender(tender_id)
        if not events:
            return True, ["No audit events recorded for this tender."]

        findings: List[str] = []
        expected_prev_hash = self.genesis_hash

        for idx, event in enumerate(events, start=1):
            # 1. Verify sequence order
            if event.sequence_no != idx:
                findings.append(
                    f"Sequence Integrity Violation at index {idx}: Expected seq {idx}, found {event.sequence_no}."
                )

            # 2. Verify previous hash pointer
            if event.previous_hash != expected_prev_hash:
                findings.append(
                    f"Hash Chain Discontinuity at event #{event.sequence_no} ({event.event_type}): "
                    f"Recorded prev_hash ({event.previous_hash[:12]}...) does not match expected parent hash ({expected_prev_hash[:12]}...)."
                )

            # 3. Re-calculate current hash from canonical event payload
            canonical_payload = json.dumps({
                "event_id": event.event_id,
                "tender_id": event.tender_id,
                "bidder_id": event.bidder_id,
                "sequence_no": event.sequence_no,
                "event_type": event.event_type,
                "details": event.event_details,
                "timestamp": event.timestamp
            }, sort_keys=True)

            recalculated_hash = hashlib.sha256((event.previous_hash + canonical_payload).encode("utf-8")).hexdigest()
            if recalculated_hash != event.current_hash:
                findings.append(
                    f"Cryptographic Tampering Detected at event #{event.sequence_no} ({event.event_type}): "
                    f"Stored hash '{event.current_hash[:16]}...' differs from calculated '{recalculated_hash[:16]}...'. "
                    "Data in event details or header has been altered!"
                )

            expected_prev_hash = event.current_hash

        is_valid = len(findings) == 0
        if is_valid:
            findings.append(f"Audit chain completely verified. Total {len(events)} events intact with valid SHA-256 links.")

        return is_valid, findings
