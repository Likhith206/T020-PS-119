"""
TENDERLENS — Explainable & Intelligent Procurement Evaluation Engine
Command Line Interface (CLI)

Usage:
    python main.py init-db
    python main.py create-tender --file data/input/tenders.csv
    python main.py import-bids --tender TND001 --file data/input/bids.csv
    python main.py evaluate TND001
    python main.py explain TND001 BID001
    python main.py explain-stage TND001 BID001 technical
    python main.py decision-graph TND001 [--bidder BID001] [--format json|text]
    python main.py scorecard TND001 BID001
    python main.py report TND001 [--format text|json]
    python main.py audit TND001
    python main.py audit-verify TND001
    python main.py risks TND001
    python main.py simulate TND001 --scenario mse_match
    python main.py award TND001
    python main.py list-tenders
    python main.py list-bids TND001
"""

import argparse
import sys
import json
from pathlib import Path

# Force UTF-8 on Windows consoles to cleanly print Rupee symbol and Indian formatting
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.storage.database import Database
from src.managers.tender_manager import TenderManager
from src.managers.bidder_manager import BidderManager
from src.core.evaluator import ProcurementEvaluator
from src.reporting.report_generator import ReportGenerator
from src.reporting.scorecard import ScorecardReporter
from src.reporting.graph_reporter import GraphReporter
from src.reporting.comparative_statement import ComparativeStatementGenerator
from src.intelligence.audit_engine import AuditEngine
from src.intelligence.risk_analyzer import RiskAnalyzer
from src.intelligence.simulator import SimulationEngine
from src.intelligence.decision_trace import DecisionTrace
from src.utils.csv_importer import CSVImporter
from src.utils.validators import validate_config_files, ValidationError
from src.utils.money_utils import format_inr


def get_db(config_dir: str = "config") -> Database:
    cfg = validate_config_files(config_dir)
    db_path = cfg["settings"].get("database_path", "database/tenderlens.db")
    return Database(db_path=db_path)


def cmd_init_db(args):
    db = get_db(args.config_dir)
    db.init_db(drop_existing=getattr(args, "reset", False))
    print("Database initialized successfully at database/tenderlens.db with schema.")
    return 0


def cmd_create_tender(args):
    db = get_db(args.config_dir)
    mgr = TenderManager(db, args.config_dir)
    tenders = CSVImporter.import_tenders(args.file)
    for t in tenders:
        mgr.create_tender(t)
        print(f"Created Tender: {t.tender_id} | Title: {t.title} | Est Cost: {format_inr(t.estimated_cost)} | Mode: {t.evaluation_method}")
    return 0


def cmd_import_bids(args):
    db = get_db(args.config_dir)
    b_mgr = BidderManager(db)
    bids_data = CSVImporter.import_bids(args.file, tender_id=args.tender)
    imported_bid_ids = set()
    imported_bidder_ids = set()

    for item in bids_data:
        bidder = item["bidder"]
        bid = item["bid"]
        b_mgr.register_bidder(bidder)
        b_mgr.register_bid(bid)
        imported_bid_ids.add(bid.bid_id)
        imported_bidder_ids.add(bid.bidder_id)
        print(f"Registered Bid: {bid.bid_id} for Bidder: {bidder.name} ({bidder.bidder_id}) on Tender: {bid.tender_id}")

    # Check companion CSV files if present in the same directory
    p = Path(args.file).parent
    exp_file = p / "experience.csv"
    if exp_file.exists():
        exps = CSVImporter.import_experience(str(exp_file))
        for e in exps:
            if e.bidder_id in imported_bidder_ids:
                b_mgr.add_experience(e)

    cert_file = p / "certificates.csv"
    if cert_file.exists():
        certs = CSVImporter.import_certificates(str(cert_file))
        for c in certs:
            if c.bidder_id in imported_bidder_ids:
                b_mgr.add_certificate(c)

    emd_file = p / "emd.csv"
    if emd_file.exists():
        emds = CSVImporter.import_emd_records(str(emd_file), tender_id=args.tender)
        for emd in emds:
            if emd.bidder_id in imported_bidder_ids:
                b_mgr.save_emd(emd)

    sched_file = p / "price_schedules.csv"
    if sched_file.exists():
        items = CSVImporter.import_price_schedules(str(sched_file))
        for itm in items:
            if itm.bid_id in imported_bid_ids:
                b_mgr.save_price_schedule_item(itm)

    scores_file = p / "technical_scores.csv"
    if scores_file.exists():
        from src.models import TechnicalScore
        from src.utils.money_utils import to_decimal
        from src.utils.date_utils import now_iso
        scores = CSVImporter.import_technical_scores(str(scores_file))
        for s in scores:
            if s["bid_id"] in imported_bid_ids:
                crit_id = f"{args.tender}_{s['criterion_code']}"
                sc = TechnicalScore(
                    score_id=s["score_id"],
                    bid_id=s["bid_id"],
                    criterion_id=crit_id,
                    evaluator_id=s["evaluator_id"],
                    raw_score=s["raw_score"],
                    remarks=s["remarks"],
                    created_at=now_iso()
                )
                b_mgr.save_technical_score(sc)

    print(f"Successfully imported bids and related documents for Tender: {args.tender}")
    return 0


def cmd_evaluate(args):
    db = get_db(args.config_dir)
    evaluator = ProcurementEvaluator(db, args.config_dir)
    print(f"Executing TENDERLENS Evaluation Pipeline for Tender: {args.tender_id}...")
    res = evaluator.evaluate_tender(args.tender_id)
    print("\n" + "=" * 70)
    print(f"EVALUATION COMPLETE | Status: {res['status']}")
    if res.get("award"):
        aw = res["award"]
        sec = res["performance_security"]
        print(f"Awarded Bidder:   {aw.awarded_bidder_id}")
        print(f"Contract Value:   {format_inr(aw.contract_value)}")
        print(f"LoA Reference:    {aw.loa_reference}")
        print(f"Security Due:     {format_inr(sec.total_security_required)} (by {sec.created_at[:10]})")
    print("=" * 70)
    print("\nUse 'python main.py decision-graph " + args.tender_id + "' to view the execution graph.")
    print("Use 'python main.py report " + args.tender_id + "' to view the full comparative dossier.")
    return 0


def cmd_explain(args):
    db = get_db(args.config_dir)
    dt = DecisionTrace(db)
    decs = dt.get_full_trace(args.tender_id, args.bidder_id)
    print(dt.format_narrative(decs))
    return 0


def cmd_explain_stage(args):
    db = get_db(args.config_dir)
    dt = DecisionTrace(db)
    # Stage alias normalizer
    stage_map = {
        "emd": "TIMELINE_AND_EMD",
        "timeline": "TIMELINE_AND_EMD",
        "eligibility": "ELIGIBILITY",
        "technical": "TECHNICAL_EVALUATION",
        "financial": "FINANCIAL_EVALUATION",
        "abnormal": "ABNORMAL_BID_ANALYSIS",
        "preference": "PROCUREMENT_PREFERENCES",
        "ranking": "RANKING",
        "validity": "BID_VALIDITY",
        "award": "AWARD_AND_SECURITY"
    }
    stage_key = stage_map.get(args.stage.lower(), args.stage.upper())
    decs = dt.get_stage_trace(args.tender_id, args.bidder_id, stage_key)
    print(dt.format_narrative(decs))
    return 0


def cmd_decision_graph(args):
    db = get_db(args.config_dir)
    reporter = GraphReporter(db)
    output = reporter.render(args.tender_id, bidder_id=args.bidder, format_type=args.format)
    print(output)
    return 0


def cmd_report(args):
    db = get_db(args.config_dir)
    gen = ReportGenerator(db)
    print(gen.generate_full_report(args.tender_id, format_type=args.format))
    return 0


def cmd_scorecard(args):
    db = get_db(args.config_dir)
    sc = ScorecardReporter(db)
    print(sc.generate(args.tender_id, args.bidder_id))
    return 0


def cmd_audit(args):
    db = get_db(args.config_dir)
    engine = AuditEngine(db)
    events = engine.repo.list_by_tender(args.tender_id)
    print("=" * 80)
    print(f"TENDERLENS | AUDIT LEDGER — TENDER: {args.tender_id}")
    print("=" * 80)
    for e in events:
        print(f"#{e.sequence_no:02d} [{e.timestamp}] TYPE: {e.event_type} | BIDDER: {e.bidder_id or 'ALL'}")
        print(f"    Hash: {e.current_hash[:32]}... | Prev: {e.previous_hash[:32]}...")
        print(f"    Details: {json.dumps(e.event_details)}")
        print("-" * 80)
    return 0


def cmd_audit_verify(args):
    db = get_db(args.config_dir)
    engine = AuditEngine(db)
    is_valid, findings = engine.verify_chain(args.tender_id)
    print("=" * 70)
    print(f"TENDERLENS | AUDIT CHAIN VERIFICATION — TENDER: {args.tender_id}")
    print("=" * 70)
    print(f"Status: {'VERIFIED - 100% UNTAMPERED' if is_valid else 'FAILED - TAMPERING DETECTED'}")
    print("\nFindings:")
    for f in findings:
        print(f"  * {f}")
    print("=" * 70)
    return 0 if is_valid else 1


def cmd_risks(args):
    db = get_db(args.config_dir)
    tender_mgr = TenderManager(db, args.config_dir)
    t = tender_mgr.get_tender(args.tender_id)
    if not t:
        print(f"Tender {args.tender_id} not found.")
        return 1
    analyzer = RiskAnalyzer(db)
    risks = analyzer.scan_risks(t)
    print("=" * 80)
    print(f"TENDERLENS | PROCUREMENT RISK INTELLIGENCE — TENDER: {args.tender_id}")
    print("=" * 80)
    if not risks:
        print("No active risk flags detected for this tender.")
    for r in risks:
        print(f"[{r.severity}] {r.risk_category} | Trigger: {r.triggering_condition}")
        if r.bidder_id:
            print(f"  Bidder: {r.bidder_id}")
        print(f"  Evidence: {r.evidence}")
        print(f"  Explanation: {r.explanation}")
        print(f"  Suggested Action: {r.suggested_action}")
        print("-" * 80)
    return 0


def cmd_simulate(args):
    db = get_db(args.config_dir)
    sim = SimulationEngine(db)
    print(f"Running isolated what-if simulation for Tender: {args.tender_id} (Scenario: {args.scenario})...")
    res = sim.run_simulation(args.tender_id, args.scenario)
    print("\n" + "=" * 70)
    print(f"SIMULATION RUN: {res['simulation_id']}")
    print(f"Scenario: {res['scenario']}")
    print("-" * 70)
    print("Original Outcome:")
    print(f"  {json.dumps(res['original_outcome'], indent=4)}")
    print("\nSimulated Outcome & Structural Diff:")
    for d in res['diff_summary']:
        print(f"  * {d}")
    print("\nSimulated Decision Graph Preview:")
    print(res["graph"].render_ascii())
    print("\nOfficial tender and audit ledger remained 100% untouched.")
    print("=" * 70)
    return 0


def cmd_award(args):
    db = get_db(args.config_dir)
    award_rows = db.execute_query("SELECT * FROM awards WHERE tender_id = ?", (args.tender_id,))
    if not award_rows:
        print(f"No contract has been awarded yet for tender {args.tender_id}. Run 'python main.py evaluate {args.tender_id}' first.")
        return 1
    aw = award_rows[0]
    sec_rows = db.execute_query("SELECT * FROM performance_securities WHERE award_id = ?", (aw["award_id"],))
    sec = sec_rows[0] if sec_rows else {}
    print("=" * 70)
    print(f"TENDERLENS | CONTRACT AWARD DETAILS — TENDER: {args.tender_id}")
    print("=" * 70)
    print(f"Award ID:              {aw['award_id']}")
    print(f"Awarded Contractor:    {aw['awarded_bidder_id']}")
    print(f"Contract Value:        {format_inr(aw['contract_value'])}")
    print(f"Award Method:          {aw['award_method']}")
    print(f"LoA Reference:         {aw['loa_reference']}")
    print(f"LoA Issue Date:        {aw['loa_issue_date']}")
    print(f"Security Due Date:     {aw['security_due_date']}")
    print(f"Award Status:          {aw['status']}")
    if sec:
        print(f"Required Security:     {format_inr(sec.get('total_security_required', '0.00'))} ({sec.get('standard_security_rate_pct', '3')}% standard)")
    print("=" * 70)
    return 0


def cmd_list_tenders(args):
    db = get_db(args.config_dir)
    mgr = TenderManager(db, args.config_dir)
    tenders = mgr.list_tenders()
    print("=" * 80)
    print(f"{'Tender ID':<12} | {'Method':<6} | {'Estimated Cost':<16} | {'Status':<16} | {'Title'}")
    print("-" * 80)
    for t in tenders:
        print(f"{t.tender_id:<12} | {t.evaluation_method:<6} | {format_inr(t.estimated_cost):<16} | {t.status:<16} | {t.title}")
    print("=" * 80)
    return 0


def cmd_list_bids(args):
    db = get_db(args.config_dir)
    b_mgr = BidderManager(db)
    bids = b_mgr.list_bids_for_tender(args.tender_id)
    print("=" * 85)
    print(f"{'Bid ID':<12} | {'Bidder ID':<12} | {'Responsiveness':<16} | {'Technical':<14} | {'Rank':<6} | {'Status'}")
    print("-" * 85)
    for b in bids:
        rank_str = f"L{b.final_rank}" if b.final_rank else "N/A"
        print(f"{b.bid_id:<12} | {b.bidder_id:<12} | {b.responsiveness_status:<16} | {b.technical_status:<14} | {rank_str:<6} | {b.final_award_status}")
    print("=" * 85)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tenderlens",
        description="TENDERLENS: Explainable & Intelligent Procurement Evaluation Engine (PS-119)"
    )
    parser.add_argument("--config-dir", default="config", help="Path to config directory")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # init-db
    p_init = subparsers.add_parser("init-db", help="Initialize SQLite database schema")
    p_init.add_argument("--reset", action="store_true", help="Drop and recreate database cleanly")

    # create-tender
    p_ct = subparsers.add_parser("create-tender", help="Create tender(s) from CSV")
    p_ct.add_argument("--file", required=True, help="Path to tenders.csv")

    # import-bids
    p_ib = subparsers.add_parser("import-bids", help="Import bids and credential schedules from CSV")
    p_ib.add_argument("--tender", required=True, help="Tender ID")
    p_ib.add_argument("--file", required=True, help="Path to bids.csv")

    # evaluate
    p_ev = subparsers.add_parser("evaluate", help="Execute complete BR-12 evaluation pipeline")
    p_ev.add_argument("tender_id", help="Tender ID to evaluate")

    # explain
    p_ex = subparsers.add_parser("explain", help="Display explainable decision trace for a bidder")
    p_ex.add_argument("tender_id", help="Tender ID")
    p_ex.add_argument("bidder_id", help="Bidder ID")

    # explain-stage
    p_es = subparsers.add_parser("explain-stage", help="Display decision trace for a specific evaluation stage")
    p_es.add_argument("tender_id", help="Tender ID")
    p_es.add_argument("bidder_id", help="Bidder ID")
    p_es.add_argument("stage", help="Stage name (e.g. emd, eligibility, technical, financial, ranking)")

    # decision-graph
    p_dg = subparsers.add_parser("decision-graph", help="Render Procurement Decision Graph")
    p_dg.add_argument("tender_id", help="Tender ID")
    p_dg.add_argument("--bidder", default=None, help="Filter graph for specific bidder ID")
    p_dg.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_dg.add_argument("--history", action="store_true", help="Include full stage history")

    # report
    p_rp = subparsers.add_parser("report", help="Generate consolidated evaluation report dossier")
    p_rp.add_argument("tender_id", help="Tender ID")
    p_rp.add_argument("--format", choices=["text", "json"], default="text", help="Report format")

    # scorecard
    p_sc = subparsers.add_parser("scorecard", help="Display technical evaluation scorecard")
    p_sc.add_argument("tender_id", help="Tender ID")
    p_sc.add_argument("bidder_id", help="Bidder ID")

    # audit
    p_au = subparsers.add_parser("audit", help="Display chronological hash-linked audit ledger")
    p_au.add_argument("tender_id", help="Tender ID")

    # audit-verify
    p_av = subparsers.add_parser("audit-verify", help="Cryptographically verify audit ledger hash chain")
    p_av.add_argument("tender_id", help="Tender ID")

    # risks
    p_rk = subparsers.add_parser("risks", help="Scan procurement risk intelligence")
    p_rk.add_argument("tender_id", help="Tender ID")

    # simulate
    p_sm = subparsers.add_parser("simulate", help="Run isolated what-if scenario simulation")
    p_sm.add_argument("tender_id", help="Tender ID")
    p_sm.add_argument("--scenario", required=True, choices=["l1_withdrawal", "mse_match", "security_failure", "abnormal_rejection"], help="Simulation scenario")

    # award
    p_aw = subparsers.add_parser("award", help="Display contract award & security status")
    p_aw.add_argument("tender_id", help="Tender ID")

    # list-tenders
    subparsers.add_parser("list-tenders", help="List all tenders")

    # list-bids
    p_lb = subparsers.add_parser("list-bids", help="List all bids for a tender")
    p_lb.add_argument("tender_id", help="Tender ID")

    return parser


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    commands = {
        "init-db": cmd_init_db,
        "create-tender": cmd_create_tender,
        "import-bids": cmd_import_bids,
        "evaluate": cmd_evaluate,
        "explain": cmd_explain,
        "explain-stage": cmd_explain_stage,
        "decision-graph": cmd_decision_graph,
        "report": cmd_report,
        "scorecard": cmd_scorecard,
        "audit": cmd_audit,
        "audit-verify": cmd_audit_verify,
        "risks": cmd_risks,
        "simulate": cmd_simulate,
        "award": cmd_award,
        "list-tenders": cmd_list_tenders,
        "list-bids": cmd_list_bids
    }

    cmd_fn = commands.get(args.command)
    if not cmd_fn:
        parser.print_help()
        sys.exit(1)

    try:
        code = cmd_fn(args)
        sys.exit(code or 0)
    except Exception as e:
        print(f"\n[ERROR] Command '{args.command}' failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
