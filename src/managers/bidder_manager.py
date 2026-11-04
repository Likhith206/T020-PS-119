"""
TENDERLENS — Bidder Manager
Handles bidder profiles, certificates, credentials, and bid registrations.
"""

from typing import List, Optional, Dict, Any
from src.storage.database import Database
from src.storage.repositories import (
    BidderRepository, BidRepository, EMDRepository, TechnicalRepository, FinancialRepository
)
from src.models import (
    Bidder, Bid, BidderExperience, BidderCertificate, EMDRecord, TechnicalScore, PriceScheduleItem
)
from src.utils.validators import ValidationError
from src.utils.date_utils import now_iso


class BidderManager:
    def __init__(self, db: Database):
        self.db = db
        self.bidder_repo = BidderRepository(db)
        self.bid_repo = BidRepository(db)
        self.emd_repo = EMDRepository(db)
        self.tech_repo = TechnicalRepository(db)
        self.fin_repo = FinancialRepository(db)

    def register_bidder(self, bidder: Bidder) -> Bidder:
        self.bidder_repo.save(bidder)
        return bidder

    def register_bid(self, bid: Bid) -> Bid:
        self.bid_repo.save(bid)
        return bid

    def add_experience(self, exp: BidderExperience) -> None:
        self.bidder_repo.add_experience(exp)

    def add_certificate(self, cert: BidderCertificate) -> None:
        self.bidder_repo.add_certificate(cert)

    def save_emd(self, emd: EMDRecord) -> None:
        self.emd_repo.save(emd)

    def save_technical_score(self, score: TechnicalScore) -> None:
        self.tech_repo.save_score(score)

    def save_price_schedule_item(self, item: PriceScheduleItem) -> None:
        self.fin_repo.save_price_schedule_item(item)

    def get_bidder(self, bidder_id: str) -> Optional[Bidder]:
        return self.bidder_repo.get_by_id(bidder_id)

    def get_bid(self, tender_id: str, bidder_id: str) -> Optional[Bid]:
        return self.bid_repo.get_by_tender_and_bidder(tender_id, bidder_id)

    def list_bids_for_tender(self, tender_id: str) -> List[Bid]:
        return self.bid_repo.list_by_tender(tender_id)
