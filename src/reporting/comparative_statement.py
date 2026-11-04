"""
TENDERLENS — Financial Comparative Statement Generator
Renders comprehensive commercial comparative statements across all evaluated bidders.
"""

from typing import List, Dict, Any
from src.storage.database import Database
from src.utils.money_utils import format_inr


class ComparativeStatementGenerator:
    def __init__(self, db: Database):
        self.db = db

    def generate(self, tender_id: str) -> str:
        rows = self.db.execute_query("""
            SELECT 
                b.bidder_id,
                bdr.name AS bidder_name,
                b.final_rank,
                b.overall_technical_score,
                fe.original_quoted_total,
                fe.arithmetic_corrected_total,
                fe.has_arithmetic_discrepancy,
                fe.final_comparative_price,
                fe.financial_score,
                fe.combined_qcbs_score,
                fe.is_abnormally_low,
                b.final_award_status
            FROM bids b
            JOIN bidders bdr ON b.bidder_id = bdr.bidder_id
            LEFT JOIN financial_evaluations fe ON b.bid_id = fe.bid_id
            WHERE b.tender_id = ? AND b.responsiveness_status = 'RESPONSIVE' AND b.technical_status = 'QUALIFIED'
            ORDER BY b.final_rank ASC
        """, (tender_id,))

        if not rows:
            return f"No qualified financial bids found for tender {tender_id}."

        lines = []
        lines.append("=" * 110)
        lines.append(f"TENDERLENS | FINANCIAL COMPARATIVE STATEMENT — TENDER: {tender_id}")
        lines.append("=" * 110)
        header = f"{'Rank':<5} | {'Bidder ID':<10} | {'Bidder Name':<24} | {'Quoted Total':<16} | {'Corrected Price':<16} | {'Tech %':<7} | {'Status':<12}"
        lines.append(header)
        lines.append("-" * 110)

        for r in rows:
            rank_str = f"L{r['final_rank']}" if r['final_rank'] else "N/A"
            orig_str = format_inr(r['original_quoted_total']) if r['original_quoted_total'] else "N/A"
            corr_str = format_inr(r['final_comparative_price']) if r['final_comparative_price'] else "N/A"
            disc_flag = " *" if r['has_arithmetic_discrepancy'] else ""
            name = (r['bidder_name'][:22] + "..") if len(r['bidder_name']) > 24 else r['bidder_name']

            lines.append(
                f"{rank_str:<5} | {r['bidder_id']:<10} | {name:<24} | {orig_str:<16} | {corr_str + disc_flag:<16} | {r['overall_technical_score']:<7} | {r['final_award_status']:<12}"
            )

        lines.append("-" * 110)
        lines.append("(*) Indicates arithmetic corrections were applied to match unit-rate calculations.")
        lines.append("=" * 110)
        return "\n".join(lines)
