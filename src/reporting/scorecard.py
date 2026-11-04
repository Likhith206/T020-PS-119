"""
TENDERLENS — Technical Scorecard Reporter
Generates detailed evaluator breakdown, weighted contributions, and cut-off verification.
"""

from typing import Optional
from src.storage.database import Database
from src.storage.repositories import TenderRepository, BidRepository, TechnicalRepository


class ScorecardReporter:
    def __init__(self, db: Database):
        self.db = db
        self.tender_repo = TenderRepository(db)
        self.bid_repo = BidRepository(db)
        self.tech_repo = TechnicalRepository(db)

    def generate(self, tender_id: str, bidder_id: str) -> str:
        bid = self.bid_repo.get_by_tender_and_bidder(tender_id, bidder_id)
        if not bid:
            return f"No bid found for Tender: {tender_id}, Bidder: {bidder_id}."

        criteria = self.tech_repo.list_criteria(tender_id)
        scores = self.tech_repo.get_scores_for_bid(bid.bid_id)

        lines = []
        lines.append("=" * 80)
        lines.append(f"TENDERLENS | TECHNICAL EVALUATION SCORECARD")
        lines.append(f"Tender: {tender_id} | Bidder: {bidder_id} | Status: {bid.technical_status}")
        lines.append("=" * 80)
        lines.append(f"{'Criterion Code':<16} | {'Name':<24} | {'Weight':<8} | {'Min %':<7} | {'Score %':<8} | {'Weighted':<8}")
        lines.append("-" * 80)

        for c in criteria:
            crit_scores = [s.raw_score for s in scores if s.criterion_id == c.criterion_id]
            avg = sum(crit_scores) / len(crit_scores) if crit_scores else 0
            weighted = (avg * c.weight_pct) / 100
            name = (c.name[:22] + "..") if len(c.name) > 24 else c.name
            lines.append(
                f"{c.code:<16} | {name:<24} | {c.weight_pct}%   | {c.min_score_pct}%   | {avg:.2f}%   | {weighted:.2f}%"
            )

        lines.append("-" * 80)
        lines.append(f"OVERALL TECHNICAL SCORE: {bid.overall_technical_score}% (Mandatory Cut-off: 70.00%)")
        lines.append(f"DETERMINATION: {'QUALIFIED (Financial Envelope Unlocked)' if bid.technical_status == 'QUALIFIED' else 'DISQUALIFIED (Financial Envelope Kept Locked)'}")
        lines.append("=" * 80)
        return "\n".join(lines)
