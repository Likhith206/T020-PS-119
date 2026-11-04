"""
TENDERLENS — Decision Trace & Explainability Engine
Generates detailed, rule-by-rule narrative explanations and mathematical proofs for every procurement determination.
"""

from typing import List, Dict, Any, Optional
from src.storage.database import Database
from src.storage.repositories import DecisionRepository
from src.models import DecisionRecord


class DecisionTrace:
    def __init__(self, db: Database):
        self.db = db
        self.repo = DecisionRepository(db)

    def get_full_trace(self, tender_id: str, bidder_id: str) -> List[DecisionRecord]:
        return self.repo.list_by_bidder(tender_id, bidder_id)

    def get_stage_trace(self, tender_id: str, bidder_id: str, stage: str) -> List[DecisionRecord]:
        return self.repo.list_by_stage(tender_id, bidder_id, stage)

    def format_narrative(self, decisions: List[DecisionRecord]) -> str:
        if not decisions:
            return "No decision records found for the requested criteria."

        lines = []
        lines.append("=" * 70)
        lines.append("TENDERLENS | EXPLAINABLE DECISION TRACE")
        lines.append("=" * 70)

        for d in decisions:
            lines.append(f"\n[RULE {d.rule_id}] STAGE: {d.evaluation_stage} | RESULT: {d.result}")
            lines.append(f"  Decision ID: {d.decision_id}")
            lines.append(f"  Explanation: {d.human_explanation}")
            lines.append(f"  Calculation: {d.calculation_details}")
            lines.append(f"  Input Snapshot: {d.input_values}")
            lines.append(f"  Required Thresholds: {d.required_thresholds}")
            if d.evidence_reference:
                lines.append(f"  Evidence: {d.evidence_reference}")
            lines.append(f"  Recorded At: {d.created_at}")
            lines.append("-" * 70)

        return "\n".join(lines)
