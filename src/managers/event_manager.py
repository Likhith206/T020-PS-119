"""
TENDERLENS — Event Manager
Tracks procurement lifecycle milestones and events in SQLite.
"""

import json
import uuid
from typing import Optional, Dict, Any, List
from src.storage.database import Database
from src.utils.date_utils import now_iso


class EventManager:
    def __init__(self, db: Database):
        self.db = db

    def record_event(
        self,
        tender_id: str,
        stage_name: str,
        event_type: str,
        bidder_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        triggered_by: str = "SYSTEM"
    ) -> str:
        event_id = str(uuid.uuid4())
        sql = """
        INSERT INTO procurement_events (
            event_id, tender_id, bidder_id, stage_name, event_type,
            event_payload, triggered_by, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        payload_json = json.dumps(payload or {}, sort_keys=True)
        with self.db.transaction() as cur:
            cur.execute(sql, (
                event_id, tender_id, bidder_id, stage_name, event_type,
                payload_json, triggered_by, now_iso()
            ))
        return event_id

    def list_events(self, tender_id: str) -> List[Dict[str, Any]]:
        rows = self.db.execute_query(
            "SELECT * FROM procurement_events WHERE tender_id = ? ORDER BY timestamp ASC",
            (tender_id,)
        )
        for r in rows:
            if r.get("event_payload"):
                r["event_payload"] = json.loads(r["event_payload"])
        return rows
