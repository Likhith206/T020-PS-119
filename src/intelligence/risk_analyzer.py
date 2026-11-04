"""
TENDERLENS — Procurement Risk Intelligence Subsystem
Evaluates systemic and bidder-specific procurement vulnerabilities across 5 categories:
COMPLIANCE, FINANCIAL, TECHNICAL, TIMELINE, and INTEGRITY.
"""

import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional
from src.models import Tender, Bid, RiskRecord
from src.storage.database import Database
from src.storage.repositories import (
    RiskRepository, BidRepository, EMDRepository, TechnicalRepository,
    FinancialRepository, AwardRepository
)
from src.utils.money_utils import to_decimal, format_inr
from src.utils.date_utils import days_between, today_iso, add_days, now_iso


class RiskAnalyzer:
    def __init__(self, db: Database):
        self.db = db
        self.risk_repo = RiskRepository(db)
        self.bid_repo = BidRepository(db)
        self.emd_repo = EMDRepository(db)
        self.tech_repo = TechnicalRepository(db)
        self.fin_repo = FinancialRepository(db)
        self.award_repo = AwardRepository(db)

    def scan_risks(self, tender: Tender) -> List[RiskRecord]:
        """Runs full risk inspection across tender and all registered bids."""
        risks: List[RiskRecord] = []
        bids = self.bid_repo.list_by_tender(tender.tender_id)

        # 1. Tender Level: Single Bid Risk
        responsive_bids = [b for b in bids if b.responsiveness_status == "RESPONSIVE"]
        if len(responsive_bids) == 1:
            r = RiskRecord(
                risk_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=responsive_bids[0].bidder_id,
                risk_category="COMPLIANCE",
                severity="HIGH",
                triggering_condition="Responsive bidder count == 1",
                evidence=f"Total bids: {len(bids)}, Responsive: 1 ({responsive_bids[0].bidder_id})",
                explanation="Single responsive bid limits market competition and price discovery.",
                suggested_action="Verify market benchmarking and ensure tender terms were not restrictive before award.",
                detected_at=now_iso()
            )
            risks.append(r)
            self.risk_repo.save(r)

        # 2. Tender Level: Approaching Validity Expiration
        validity_end = add_days(tender.bid_opening_date, tender.bid_validity_days)
        days_left = days_between(today_iso(), validity_end)
        if 0 <= days_left <= 15 and tender.status not in ("AWARDED", "CANCELLED", "RETENDER_TRIGGERED"):
            r = RiskRecord(
                risk_id=str(uuid.uuid4()),
                tender_id=tender.tender_id,
                bidder_id=None,
                risk_category="TIMELINE",
                severity="CRITICAL",
                triggering_condition=f"Days until validity expiry ({days_left}) <= 15 days",
                evidence=f"Validity end date: {validity_end}, Today: {today_iso()}",
                explanation="Bid validity expiring soon without finalized contract award.",
                suggested_action="Initiate formal 30-day validity extension request under BR-08 immediately.",
                detected_at=now_iso()
            )
            risks.append(r)
            self.risk_repo.save(r)

        # 3. Bidder Level Risks
        for bid in bids:
            # EMD BG Expiry Risk
            emd = self.emd_repo.get_by_bidder(tender.tender_id, bid.bidder_id)
            if emd and emd.payment_mode == "BG" and emd.valid_until:
                bg_days_left = days_between(today_iso(), emd.valid_until)
                if bg_days_left < 30 and emd.status == "VALID":
                    r = RiskRecord(
                        risk_id=str(uuid.uuid4()),
                        tender_id=tender.tender_id,
                        bidder_id=bid.bidder_id,
                        risk_category="TIMELINE",
                        severity="HIGH",
                        triggering_condition=f"BG remaining validity ({bg_days_left} days) < 30 days",
                        evidence=f"BG valid until: {emd.valid_until}",
                        explanation="Bank Guarantee securing EMD is approaching expiration.",
                        suggested_action="Issue formal notice to bidder to revalidate and extend BG.",
                        detected_at=now_iso()
                    )
                    risks.append(r)
                    self.risk_repo.save(r)

            # Technical Score Cut-off Borderline Risk
            if bid.technical_status == "QUALIFIED":
                score = bid.overall_technical_score
                if Decimal("70.00") <= score <= Decimal("72.50"):
                    r = RiskRecord(
                        risk_id=str(uuid.uuid4()),
                        tender_id=tender.tender_id,
                        bidder_id=bid.bidder_id,
                        risk_category="TECHNICAL",
                        severity="MEDIUM",
                        triggering_condition=f"Overall score {score}% is within 2.5% of 70% cutoff",
                        evidence=f"Score: {score}%",
                        explanation="Bidder marginally crossed the technical threshold; delivery capacity requires close scrutiny.",
                        suggested_action="Ensure strict milestone monitoring during project execution.",
                        detected_at=now_iso()
                    )
                    risks.append(r)
                    self.risk_repo.save(r)

            # Abnormally Low Price Risk
            fe = self.fin_repo.get_evaluation(bid.bid_id)
            if fe and fe.is_abnormally_low:
                r = RiskRecord(
                    risk_id=str(uuid.uuid4()),
                    tender_id=tender.tender_id,
                    bidder_id=bid.bidder_id,
                    risk_category="FINANCIAL",
                    severity="HIGH",
                    triggering_condition="Price is below 85% of estimated cost",
                    evidence=f"Evaluated price: {format_inr(fe.final_comparative_price)}, Shortfall sec: {format_inr(fe.additional_security_required)}",
                    explanation="Abnormally low bid presents risks of sub-standard quality, contract default, or mid-project abandonment.",
                    suggested_action="Mandate additional performance security deposit before signing contract.",
                    detected_at=now_iso()
                )
                risks.append(r)
                self.risk_repo.save(r)

        return risks
