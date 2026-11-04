"""
TENDERLENS — Decision Graph Reporter
Provides terminal visualization and JSON export of Procurement Decision Graphs.
"""

import json
from typing import Optional, Dict, Any
from src.storage.database import Database
from src.core.decision_graph import ProcurementDecisionGraph


class GraphReporter:
    def __init__(self, db: Database):
        self.db = db

    def render(self, tender_id: str, bidder_id: Optional[str] = None, format_type: str = "text") -> str:
        graph = ProcurementDecisionGraph.reconstruct_from_db(self.db, tender_id, bidder_id)
        if format_type.lower() == "json":
            return json.dumps(graph.to_dict(), indent=2)
        else:
            return graph.render_ascii()
