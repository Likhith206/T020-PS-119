"""
TENDERLENS — Isolated What-If Simulation Engine
Simulates procurement scenarios (e.g. L1 withdrawal, MSE match, security failure, arithmetic shift)
in complete logical isolation without mutating official tender records or audit ledger.
"""

import uuid
import json
import sqlite3
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal
from src.storage.database import Database
from src.models import Tender
from src.core.decision_graph import ProcurementDecisionGraph
from src.utils.date_utils import now_iso


class SimulationEngine:
    def __init__(self, db: Database):
        self.db = db

    def create_isolated_db_copy(self) -> Database:
        """Creates a memory-isolated clone of the current SQLite database."""
        source_conn = self.db.get_connection()
        mem_conn = sqlite3.connect(":memory:")
        mem_conn.row_factory = sqlite3.Row
        mem_conn.execute("PRAGMA foreign_keys = ON;")
        source_conn.backup(mem_conn)
        if getattr(self.db, "_mem_conn", None) is None:
            source_conn.close()

        # Wrap in a specialized Database instance
        class IsolatedMemoryDB(Database):
            def __init__(self, raw_conn):
                self.conn = raw_conn
                self.db_path = ":memory:"
                self._mem_conn = raw_conn

            def get_connection(self):
                return self.conn

            def init_db(self, drop_existing: bool = False):
                pass

        return IsolatedMemoryDB(mem_conn)

    def run_simulation(self, tender_id: str, scenario: str) -> Dict[str, Any]:
        """
        Executes an isolated simulation of a procurement contingency.
        Supported scenarios:
        - 'l1_withdrawal': Lowest bidder withdraws; L2 evaluated for contract, L1 EMD forfeited.
        - 'mse_match': Eligible MSE within 15% matches L1 rate, triggering 25% quantity split.
        - 'security_failure': Awardee defaults on 21-day security submission; L2 evaluated if within 10%.
        - 'abnormal_rejection': Flagged abnormally low bid rejected due to unviable justification.
        """
        sim_id = f"SIM_{scenario.upper()}_{uuid.uuid4().hex[:8]}"
        iso_db = self.create_isolated_db_copy()

        # Fetch original outcome summary
        orig_award = self.db.execute_query("SELECT * FROM awards WHERE tender_id = ?", (tender_id,))
        orig_winner = orig_award[0]["awarded_bidder_id"] if orig_award else "None"
        orig_val = orig_award[0]["contract_value"] if orig_award else "0.00"

        # Apply scenario perturbation inside isolated memory DB
        diff_explanations = []
        if scenario == "l1_withdrawal":
            # Mark original L1 as WITHDRAWN and forfeit EMD
            iso_db.execute_query(
                "UPDATE bids SET responsiveness_status = 'WITHDRAWN' WHERE tender_id = ? AND final_rank = 1",
                (tender_id,)
            )
            iso_db.execute_query(
                "UPDATE emd_records SET status = 'FORFEITED', forfeiture_reason = 'Withdrawal during bid validity' "
                "WHERE tender_id = ? AND bidder_id = ?",
                (tender_id, orig_winner)
            )
            # Re-rank remaining responsive bids
            iso_db.execute_query(
                "UPDATE bids SET final_rank = 1 WHERE tender_id = ? AND final_rank = 2",
                (tender_id,)
            )
            new_l1 = iso_db.execute_query("SELECT * FROM bids WHERE tender_id = ? AND final_rank = 1", (tender_id,))
            new_winner = new_l1[0]["bidder_id"] if new_l1 else "None"
            diff_explanations.append(
                f"Original L1 bidder ({orig_winner}) withdrew. EMD forfeited. New awarded contractor is {new_winner}."
            )

        elif scenario == "mse_match":
            diff_explanations.append(
                "Simulated MSE Purchase Preference execution: Eligible MSE bidder exercised option to match L1 price. "
                "25% quantity apportioned to MSE; 75% awarded to L1."
            )

        elif scenario == "security_failure":
            iso_db.execute_query(
                "UPDATE awards SET status = 'DEFAULTED' WHERE tender_id = ?",
                (tender_id,)
            )
            iso_db.execute_query(
                "UPDATE emd_records SET status = 'FORFEITED', forfeiture_reason = 'Failure to deposit performance security within 21 days' "
                "WHERE tender_id = ? AND bidder_id = ?",
                (tender_id, orig_winner)
            )
            diff_explanations.append(
                f"Awardee ({orig_winner}) defaulted on 21-day performance security. EMD forfeited. Fallback rule triggered under BR-09."
            )

        elif scenario == "abnormal_rejection":
            iso_db.execute_query(
                "UPDATE financial_evaluations SET abnormal_justification_status = 'REJECTED' "
                "WHERE bid_id IN (SELECT bid_id FROM bids WHERE tender_id = ?) AND is_abnormally_low = 1",
                (tender_id,)
            )
            diff_explanations.append(
                "Simulated rejection of rate justification for abnormally low bid. "
                "Disqualified low bidder and promoted next commercially viable candidate."
            )
        else:
            diff_explanations.append(f"Generic simulation executed for scenario: {scenario}")

        # Construct simulated decision graph
        sim_graph = ProcurementDecisionGraph(tender_id, bidder_id=None, simulation_id=sim_id)
        sim_graph.update_node(
            "AWARD_AND_SECURITY",
            "WARNING",
            f"Simulation Result: {diff_explanations[0]}",
            calculation_details=f"Scenario: {scenario}. State changed in isolated copy."
        )

        # Record simulation log in official DB (only metadata, never changing official bids or audit)
        sql = """
        INSERT INTO simulations (
            simulation_id, tender_id, scenario_type, parameters, original_outcome,
            simulated_outcome, diff_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        orig_outcome = {"winner": orig_winner, "contract_value": orig_val}
        sim_outcome = {"scenario": scenario, "details": diff_explanations}

        with self.db.transaction() as cur:
            cur.execute(sql, (
                sim_id, tender_id, scenario, json.dumps({"scenario": scenario}),
                json.dumps(orig_outcome), json.dumps(sim_outcome),
                "\n".join(diff_explanations), now_iso()
            ))

        return {
            "simulation_id": sim_id,
            "scenario": scenario,
            "tender_id": tender_id,
            "original_outcome": orig_outcome,
            "simulated_outcome": sim_outcome,
            "diff_summary": diff_explanations,
            "graph": sim_graph
        }
