"""
TENDERLENS — Comprehensive Procurement Report Generator (FR-14)
Compiles multi-stage procurement dossiers including tender summary, responsiveness,
technical evaluations, financial comparative statements, preference allocations, awards, and audit traces.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.storage.database import Database
from src.reporting.comparative_statement import ComparativeStatementGenerator
from src.reporting.graph_reporter import GraphReporter
from src.intelligence.risk_analyzer import RiskAnalyzer
from src.intelligence.audit_engine import AuditEngine
from src.utils.money_utils import format_inr


class ReportGenerator:
    def __init__(self, db: Database):
        self.db = db
        self.comp_gen = ComparativeStatementGenerator(db)
        self.graph_gen = GraphReporter(db)
        self.risk_analyzer = RiskAnalyzer(db)
        self.audit_engine = AuditEngine(db)

    def generate_full_report(self, tender_id: str, format_type: str = "text") -> str:
        tender_rows = self.db.execute_query("SELECT * FROM tenders WHERE tender_id = ?", (tender_id,))
        if not tender_rows:
            return f"Tender {tender_id} not found."
        tender = tender_rows[0]

        bids = self.db.execute_query("SELECT * FROM bids WHERE tender_id = ?", (tender_id,))
        award = self.db.execute_query("SELECT * FROM awards WHERE tender_id = ?", (tender_id,))
        prefs = self.db.execute_query("SELECT * FROM preference_allocations WHERE tender_id = ?", (tender_id,))
        risks = self.db.execute_query("SELECT * FROM risk_records WHERE tender_id = ?", (tender_id,))
        audit_valid, audit_notes = self.audit_engine.verify_chain(tender_id)

        if format_type.lower() == "json":
            data = {
                "tender": tender,
                "bids": bids,
                "award": award[0] if award else None,
                "preferences": prefs,
                "risks": risks,
                "audit": {"valid": audit_valid, "notes": audit_notes}
            }
            return json.dumps(data, indent=2)

        # Text terminal formatting
        lines = []
        lines.append("=" * 80)
        lines.append("TENDERLENS — CONSOLIDATED PROCUREMENT EVALUATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Tender ID:        {tender['tender_id']}")
        lines.append(f"Title:            {tender['title']}")
        lines.append(f"Estimated Cost:   {format_inr(tender['estimated_cost'])}")
        lines.append(f"Evaluation Mode:  {tender['evaluation_method']}")
        lines.append(f"Current Status:   {tender['status']}")
        lines.append(f"Total Bids Recd:  {len(bids)}")
        lines.append("-" * 80)

        # Comparative statement
        lines.append("\n" + self.comp_gen.generate(tender_id))

        # Award Section
        lines.append("\nCONTRACT AWARD DETAILS:")
        if award:
            a = award[0]
            lines.append(f"  Awarded Contractor: {a['awarded_bidder_id']}")
            lines.append(f"  Final Contract Val: {format_inr(a['contract_value'])}")
            lines.append(f"  LoA Reference:      {a['loa_reference']}")
            lines.append(f"  LoA Issue Date:     {a['loa_issue_date']}")
            lines.append(f"  Security Due Date:  {a['security_due_date']} (within 21 days)")
        else:
            lines.append("  Contract not yet awarded or re-tender triggered.")

        # Preferences
        if prefs:
            lines.append("\nPROCUREMENT PREFERENCES ALLOCATED:")
            for p in prefs:
                lines.append(f"  - Bidder {p['bidder_id']} ({p['preference_type']}): {p['allocated_quantity_pct']}% @ {format_inr(p['awarded_price'])}")

        # Risks
        if risks:
            lines.append(f"\nIDENTIFIED RISKS ({len(risks)} Active Findings):")
            for r in risks:
                lines.append(f"  [{r['severity']}] {r['risk_category']}: {r['explanation']} -> Action: {r['suggested_action']}")
        else:
            lines.append("\nIDENTIFIED RISKS: None detected.")

        # Audit Chain Verification
        lines.append(f"\nAUDIT LEDGER INTEGRITY: {'VERIFIED (100% Intact SHA-256 Linkage)' if audit_valid else 'TAMPERING DETECTED'}")
        for note in audit_notes:
            lines.append(f"  * {note}")

        lines.append("=" * 80)
        return "\n".join(lines)
