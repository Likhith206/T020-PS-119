"""
TENDERLENS — Tender Manager
Handles lifecycle, validation, criteria setup, and state of public procurement tenders.
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from src.storage.database import Database
from src.storage.repositories import TenderRepository, TechnicalRepository
from src.models import Tender, TechnicalCriterion
from src.utils.date_utils import now_iso, parse_date
from src.utils.money_utils import to_decimal
from src.utils.validators import ValidationError, validate_config_files


class TenderManager:
    def __init__(self, db: Database, config_dir: str = "config"):
        self.db = db
        self.tender_repo = TenderRepository(db)
        self.tech_repo = TechnicalRepository(db)
        self.configs = validate_config_files(config_dir)

    def create_tender(self, tender: Tender, custom_criteria: Optional[List[Dict[str, Any]]] = None) -> Tender:
        """Saves a tender and populates its technical scoring criteria."""
        existing = self.tender_repo.get_by_id(tender.tender_id)
        if existing:
            raise ValidationError(f"Tender with ID {tender.tender_id} already exists.")

        self.tender_repo.save(tender)

        # Initialize technical criteria
        criteria_to_add = custom_criteria or self.configs["scoring_defaults"].get("default_technical_criteria", [])
        for c in criteria_to_add:
            crit = TechnicalCriterion(
                criterion_id=f"{tender.tender_id}_{c['code']}",
                tender_id=tender.tender_id,
                code=c["code"],
                name=c["name"],
                weight_pct=to_decimal(c["weight_pct"]),
                min_score_pct=to_decimal(c.get("min_score_pct", "60.00")),
                description=c.get("description", ""),
                created_at=now_iso()
            )
            self.tech_repo.save_criterion(crit)

        return tender

    def get_tender(self, tender_id: str) -> Optional[Tender]:
        return self.tender_repo.get_by_id(tender_id)

    def list_tenders(self) -> List[Tender]:
        return self.tender_repo.list_all()

    def update_status(self, tender_id: str, new_status: str) -> None:
        tender = self.get_tender(tender_id)
        if not tender:
            raise ValidationError(f"Tender {tender_id} not found.")
        tender.status = new_status
        tender.updated_at = now_iso()
        self.tender_repo.save(tender)
