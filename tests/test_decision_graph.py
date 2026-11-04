"""
TENDERLENS — Decision Graph Unit Tests (Core Differentiator)
Tests 9-node DAG structure, cascading blockage logic, database persistence, and reconstruction.
"""

from src.core.decision_graph import ProcurementDecisionGraph
from src.storage.repositories import TenderRepository, BidderRepository


def test_decision_graph_initial_structure(sample_tender, sample_bid):
    graph = ProcurementDecisionGraph(sample_tender.tender_id, sample_bid.bidder_id)
    assert len(graph.nodes) == 9
    assert len(graph.edges) == 8
    assert graph.nodes["TIMELINE_AND_EMD"].stage_order == 1
    assert graph.nodes["AWARD_AND_SECURITY"].stage_order == 9


def test_decision_graph_cascading_blockage(sample_tender, sample_bid):
    graph = ProcurementDecisionGraph(sample_tender.tender_id, sample_bid.bidder_id)

    # Fail technical evaluation (Stage 3)
    graph.update_node("TECHNICAL_EVALUATION", "FAILED", "Score below 70%")

    assert graph.nodes["TECHNICAL_EVALUATION"].execution_status == "FAILED"
    # All downstream nodes (4 through 9) must be automatically BLOCKED
    assert graph.nodes["FINANCIAL_EVALUATION"].execution_status == "BLOCKED"
    assert graph.nodes["ABNORMAL_BID_ANALYSIS"].execution_status == "BLOCKED"
    assert graph.nodes["PROCUREMENT_PREFERENCES"].execution_status == "BLOCKED"
    assert graph.nodes["RANKING"].execution_status == "BLOCKED"
    assert graph.nodes["BID_VALIDITY"].execution_status == "BLOCKED"
    assert graph.nodes["AWARD_AND_SECURITY"].execution_status == "BLOCKED"


def test_decision_graph_persistence_and_reconstruction(mem_db, sample_tender, sample_bid, sample_bidder):
    TenderRepository(mem_db).save(sample_tender)
    BidderRepository(mem_db).save(sample_bidder)

    graph = ProcurementDecisionGraph(sample_tender.tender_id, sample_bid.bidder_id)
    graph.update_node("TIMELINE_AND_EMD", "PASSED", "EMD Validated")
    graph.persist(mem_db)

    # Reconstruct from DB
    reconstructed = ProcurementDecisionGraph.reconstruct_from_db(
        mem_db, sample_tender.tender_id, sample_bid.bidder_id
    )
    assert reconstructed.nodes["TIMELINE_AND_EMD"].execution_status == "PASSED"
    assert reconstructed.nodes["TIMELINE_AND_EMD"].decision_explanation == "EMD Validated"
    assert len(reconstructed.nodes) == 9
