"""
TENDERLENS — Procurement Decision Graph (Core Differentiator)
Models procurement evaluation as an explicit directed acyclic graph (DAG) of decision nodes and dependency edges.
Supports dependency-driven execution, cascading blockages, SQLite persistence, and historical reconstruction.
"""

import uuid
from typing import List, Dict, Any, Optional
from src.models import GraphNode, GraphEdge
from src.storage.database import Database
from src.storage.repositories import DecisionGraphRepository
from src.utils.date_utils import now_iso

STAGE_SEQUENCE = [
    (1, "TIMELINE_AND_EMD", ["BR-02"]),
    (2, "ELIGIBILITY", ["BR-01"]),
    (3, "TECHNICAL_EVALUATION", ["BR-03"]),
    (4, "FINANCIAL_EVALUATION", ["BR-04"]),
    (5, "ABNORMAL_BID_ANALYSIS", ["BR-07"]),
    (6, "PROCUREMENT_PREFERENCES", ["BR-05"]),
    (7, "RANKING", ["BR-06", "BR-10"]),
    (8, "BID_VALIDITY", ["BR-08"]),
    (9, "AWARD_AND_SECURITY", ["BR-09", "BR-11"])
]


class ProcurementDecisionGraph:
    def __init__(self, tender_id: str, bidder_id: Optional[str] = None, simulation_id: Optional[str] = None):
        self.tender_id = tender_id
        self.bidder_id = bidder_id
        self.simulation_id = simulation_id
        self.is_simulation = simulation_id is not None
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._initialize_graph_structure()

    def _initialize_graph_structure(self) -> None:
        """Instantiates default nodes and sequential dependency edges."""
        prev_node: Optional[GraphNode] = None

        for order, stage_name, rule_ids in STAGE_SEQUENCE:
            node_key = f"{self.bidder_id or 'TENDER'}_{stage_name}"
            node_id = f"ND_{self.tender_id}_{node_key}"
            if self.is_simulation:
                node_id = f"SIM_{self.simulation_id}_{node_id}"

            node = GraphNode(
                node_id=node_id,
                tender_id=self.tender_id,
                bidder_id=self.bidder_id,
                stage_name=stage_name,
                stage_order=order,
                business_rule_ids=rule_ids,
                execution_status="PENDING",
                input_snapshot={},
                output_snapshot={},
                calculation_details="",
                decision_explanation="",
                evidence_reference="",
                execution_timestamp=now_iso(),
                is_simulation=self.is_simulation,
                simulation_id=self.simulation_id
            )
            self.nodes[stage_name] = node

            if prev_node is not None:
                edge_id = f"ED_{prev_node.node_id}_{node.node_id}"
                edge = GraphEdge(
                    edge_id=edge_id,
                    tender_id=self.tender_id,
                    source_node_id=prev_node.node_id,
                    target_node_id=node.node_id,
                    dependency_condition=f"{prev_node.stage_name} MUST PASS",
                    dependency_result="BLOCKED",
                    explanation=f"Execution of {node.stage_name} depends on successful completion of {prev_node.stage_name}.",
                    is_simulation=self.is_simulation,
                    simulation_id=self.simulation_id
                )
                self.edges.append(edge)

            prev_node = node

    def update_node(
        self,
        stage_name: str,
        status: str,
        explanation: str,
        calculation_details: str = "",
        input_snapshot: Optional[Dict[str, Any]] = None,
        output_snapshot: Optional[Dict[str, Any]] = None,
        evidence: str = ""
    ) -> None:
        """Updates a node's state and cascades blockages to downstream dependent nodes if failed."""
        if stage_name not in self.nodes:
            return

        node = self.nodes[stage_name]
        node.execution_status = status
        node.decision_explanation = explanation
        node.calculation_details = calculation_details
        node.execution_timestamp = now_iso()
        if input_snapshot:
            node.input_snapshot = input_snapshot
        if output_snapshot:
            node.output_snapshot = output_snapshot
        if evidence:
            node.evidence_reference = evidence

        # Cascade blockage if node failed
        if status in ("FAILED", "BLOCKED"):
            self._cascade_blockage(node.stage_order, reason=f"Upstream stage '{stage_name}' failed or was blocked.")

    def _cascade_blockage(self, failed_order: int, reason: str) -> None:
        """Sets all downstream nodes to BLOCKED."""
        for name, n in self.nodes.items():
            if n.stage_order > failed_order:
                n.execution_status = "BLOCKED"
                n.decision_explanation = reason
                n.calculation_details = "Execution inhibited by Procurement Decision Graph dependency rule."
                n.execution_timestamp = now_iso()

        for edge in self.edges:
            # Update edge results
            source = next((n for n in self.nodes.values() if n.node_id == edge.source_node_id), None)
            if source and source.stage_order >= failed_order:
                edge.dependency_result = "UNSATISFIED"

    def persist(self, db: Database) -> None:
        """Saves current graph state to SQLite."""
        repo = DecisionGraphRepository(db)
        for node in self.nodes.values():
            repo.save_node(node)
        for edge in self.edges:
            repo.save_edge(edge)

    @classmethod
    def reconstruct_from_db(
        cls,
        db: Database,
        tender_id: str,
        bidder_id: Optional[str] = None,
        simulation_id: Optional[str] = None
    ) -> "ProcurementDecisionGraph":
        """Reconstructs the Decision Graph instance from persistent SQLite records."""
        repo = DecisionGraphRepository(db)
        nodes = repo.get_nodes(tender_id, bidder_id, simulation_id)
        edges = repo.get_edges(tender_id, simulation_id)

        graph = cls(tender_id, bidder_id, simulation_id)
        if nodes:
            graph.nodes = {n.stage_name: n for n in nodes}
        if edges:
            graph.edges = edges
        return graph

    def to_dict(self) -> Dict[str, Any]:
        """Serializes graph to JSON-compatible dictionary."""
        return {
            "tender_id": self.tender_id,
            "bidder_id": self.bidder_id,
            "is_simulation": self.is_simulation,
            "simulation_id": self.simulation_id,
            "nodes": [
                {
                    "node_id": n.node_id,
                    "stage_name": n.stage_name,
                    "stage_order": n.stage_order,
                    "rules": n.business_rule_ids,
                    "status": n.execution_status,
                    "explanation": n.decision_explanation,
                    "calculation": n.calculation_details,
                    "evidence": n.evidence_reference,
                    "timestamp": n.execution_timestamp
                }
                for n in sorted(self.nodes.values(), key=lambda x: x.stage_order)
            ],
            "edges": [
                {
                    "edge_id": e.edge_id,
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "condition": e.dependency_condition,
                    "result": e.dependency_result,
                    "explanation": e.explanation
                }
                for e in self.edges
            ]
        }

    def render_ascii(self) -> str:
        """Renders clear, terminal-friendly ASCII decision graph view."""
        lines = []
        lines.append("=" * 65)
        lines.append("TENDERLENS | PROCUREMENT DECISION GRAPH")
        lines.append(f"Tender: {self.tender_id} | Bidder: {self.bidder_id or 'AGGREGATE'}")
        if self.is_simulation:
            lines.append(f"SIMULATION RUN: {self.simulation_id}")
        lines.append("=" * 65)

        status_symbols = {
            "PASSED": "[PASS]",
            "FAILED": "[FAIL]",
            "WARNING": "[WARN]",
            "BLOCKED": "[BLOCK]",
            "PENDING": "[PEND]",
            "SKIPPED": "[SKIP]",
            "RUNNING": "[RUN ]"
        }

        sorted_nodes = sorted(self.nodes.values(), key=lambda x: x.stage_order)
        for idx, node in enumerate(sorted_nodes, start=1):
            tag = status_symbols.get(node.execution_status, "[????]")
            lines.append(f"\n{tag} {node.stage_order:02d}. {node.stage_name}")
            if node.decision_explanation:
                lines.append(f"    Decision: {node.decision_explanation}")
            if node.calculation_details:
                lines.append(f"    Calculation: {node.calculation_details}")
            if idx < len(sorted_nodes):
                lines.append("          ↓")

        lines.append("\n" + "-" * 65)
        # Determine overall terminal state
        has_failed = any(n.execution_status in ("FAILED", "BLOCKED") for n in sorted_nodes)
        all_passed = all(n.execution_status in ("PASSED", "WARNING", "SKIPPED") for n in sorted_nodes)

        final_status = "QUALIFIED / AWARDABLE" if all_passed else ("DISQUALIFIED / BLOCKED" if has_failed else "IN PROGRESS")
        lines.append(f"FINAL DECISION STATUS: {final_status}")
        lines.append("=" * 65)
        return "\n".join(lines)
