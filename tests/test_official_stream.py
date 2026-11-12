"""
Automated tests for the official faculty data pack and commands.txt stream execution.
"""

from pathlib import Path
from src.official_stream import OfficialStreamRunner


def test_official_stream_execution(tmp_path):
    out_dir = tmp_path / "reports"
    runner = OfficialStreamRunner(data_dir="data/official", out_dir=str(out_dir))
    runner.execute_command_stream("data/official/commands.txt")

    # 1. Check all four output CSV files exist
    assert (out_dir / "responsiveness.csv").exists()
    assert (out_dir / "tech_scorecard.csv").exists()
    assert (out_dir / "comparative_statement.csv").exists()
    assert (out_dir / "award.csv").exists()

    # 2. Check responsiveness assertions
    # BID-002: BG ends 44 days (less than 45 days) -> FAIL
    assert runner.responsiveness_results["BID-002"]["emd_status"] == "FAIL"
    assert runner.responsiveness_results["BID-002"]["status"] == "NON_RESPONSIVE"

    # BID-030: BG ends exactly 45 days -> PASS
    assert runner.responsiveness_results["BID-030"]["emd_status"] == "PASS"

    # BID-007: Expired MSE certificate -> FAIL
    assert runner.responsiveness_results["BID-007"]["emd_status"] == "FAIL"

    # BID-009: Blacklisted before opening -> FAIL
    assert runner.responsiveness_results["BID-009"]["blacklist_check"] == "FAIL"

    # BID-029: 80% work completed 7 years + 2 days ago -> FAIL experience
    assert runner.responsiveness_results["BID-029"]["experience_check"] == "FAIL"

    # 3. Check technical evaluations
    # BID-018: Exact 60% criterion and exact 70.00% overall -> PASS
    assert runner.tech_scorecards["BID-018"]["passed"] is True
    assert runner.tech_scorecards["BID-018"]["overall_score"] == 70.00

    # BID-019: C2 averages 58.00 (< 60) -> TECHNICALLY_DISQUALIFIED
    assert runner.tech_scorecards["BID-019"]["passed"] is False

    # 4. Check awards
    awards = {aw["tender_id"]: aw for aw in runner.award_records}
    # TND-01: Winner defaulted, next ranked BID-014 awarded
    assert any(aw["bid_id"] == "BID-014" and aw["basis"] == "NEXT_RANKED" for aw in runner.award_records)
    # TND-02: Reserved for MSE, BID-023 awarded 100% quantity (2000)
    assert any(aw["bid_id"] == "BID-023" and aw["quantity"] == 2000 and aw["basis"] == "MSE_MATCH" for aw in runner.award_records)
    # TND-04: Negotiated L1
    assert any(aw["bid_id"] == "BID-015" and aw["basis"] == "NEGOTIATED" for aw in runner.award_records)
