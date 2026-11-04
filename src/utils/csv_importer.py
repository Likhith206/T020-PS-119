"""
TENDERLENS — CSV Import Engine
Provides robust importing of tenders, bids, certificates, experience, EMD, technical scores,
and price schedules with comprehensive schema verification and error detection.
"""

import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal
from src.utils.validators import ValidationError, validate_csv_columns, validate_tender_dict
from src.models import (
    Tender, Bidder, Bid, BidderExperience, BidderCertificate,
    EMDRecord, TechnicalScore, PriceScheduleItem
)
from src.utils.money_utils import to_decimal
from src.utils.date_utils import now_iso, today_iso


class CSVImporter:
    @staticmethod
    def import_tenders(file_path: str) -> List[Tender]:
        p = Path(file_path)
        if not p.exists():
            raise ValidationError(f"Tenders file not found: {file_path}")

        tenders = []
        required_cols = [
            "tender_id", "title", "estimated_cost", "bid_opening_date",
            "bid_closing_date", "evaluation_method"
        ]

        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            validate_csv_columns(reader.fieldnames or [], required_cols, "Tenders CSV")
            for line_no, row in enumerate(reader, start=2):
                try:
                    validate_tender_dict(row)
                    est = to_decimal(row["estimated_cost"])
                    # If emd_amount is not explicitly given, calculate 2% capped at 50 Lakhs
                    emd_str = row.get("emd_amount", "").strip()
                    if emd_str:
                        emd_amt = to_decimal(emd_str)
                    else:
                        two_pct = (est * Decimal("0.02"))
                        cap = Decimal("5000000.00")
                        emd_amt = min(two_pct, cap)

                    t = Tender(
                        tender_id=row["tender_id"].strip(),
                        title=row["title"].strip(),
                        description=row.get("description", "").strip(),
                        estimated_cost=est,
                        currency=row.get("currency", "INR").strip(),
                        bid_opening_date=row["bid_opening_date"].strip(),
                        bid_closing_date=row["bid_closing_date"].strip(),
                        bid_validity_days=int(row.get("bid_validity_days", 90)),
                        evaluation_method=row["evaluation_method"].strip().upper(),
                        qcbs_tech_weight=to_decimal(row.get("qcbs_tech_weight", "70.00")),
                        qcbs_fin_weight=to_decimal(row.get("qcbs_fin_weight", "30.00")),
                        emd_required=row.get("emd_required", "1") in ("1", "True", "true", "yes"),
                        emd_amount=emd_amt,
                        mse_relax_enabled=row.get("mse_relax_enabled", "0") in ("1", "True", "true", "yes"),
                        single_bid_allowed=row.get("single_bid_allowed", "0") in ("1", "True", "true", "yes"),
                        is_reserved_item=row.get("is_reserved_item", "0") in ("1", "True", "true", "yes"),
                        status="PUBLISHED",
                        created_at=row.get("created_at", now_iso()),
                        updated_at=now_iso()
                    )
                    tenders.append(t)
                except Exception as e:
                    raise ValidationError(f"Error parsing tenders CSV at line {line_no}: {e}")

        return tenders

    @staticmethod
    def import_bids(file_path: str, tender_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Imports bids with bidder details."""
        p = Path(file_path)
        if not p.exists():
            raise ValidationError(f"Bids file not found: {file_path}")

        records = []
        required_cols = ["bid_id", "tender_id", "bidder_id", "bidder_name", "organization_type"]

        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            validate_csv_columns(reader.fieldnames or [], required_cols, "Bids CSV")
            for line_no, row in enumerate(reader, start=2):
                t_id = row["tender_id"].strip()
                if tender_id and t_id != tender_id:
                    continue  # Filter for requested tender
                records.append({
                    "bid": Bid(
                        bid_id=row["bid_id"].strip(),
                        tender_id=t_id,
                        bidder_id=row["bidder_id"].strip(),
                        submission_timestamp=row.get("submission_timestamp", now_iso()).strip(),
                        technical_envelope_opened=False,
                        financial_envelope_opened=False,
                        responsiveness_status="SUBMITTED",
                        technical_status="PENDING",
                        overall_technical_score=Decimal("0.00"),
                        financial_status="LOCKED",
                        final_rank=None,
                        final_award_status="NONE",
                        created_at=now_iso()
                    ),
                    "bidder": Bidder(
                        bidder_id=row["bidder_id"].strip(),
                        name=row["bidder_name"].strip(),
                        organization_type=row["organization_type"].strip(),
                        registration_no=row.get("registration_no", "").strip() or None,
                        pan_no=row.get("pan_no", "").strip() or None,
                        gstin=row.get("gstin", "").strip() or None,
                        email=row.get("email", "").strip() or None,
                        phone=row.get("phone", "").strip() or None,
                        registered_address=row.get("registered_address", "").strip() or None,
                        is_blacklisted=row.get("is_blacklisted", "0") in ("1", "True", "true", "yes"),
                        blacklisted_since=row.get("blacklisted_since", "").strip() or None,
                        blacklisting_reason=row.get("blacklisting_reason", "").strip() or None,
                        created_at=now_iso()
                    )
                })
        return records

    @staticmethod
    def import_experience(file_path: str) -> List[BidderExperience]:
        p = Path(file_path)
        if not p.exists():
            return []
        exps = []
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                exps.append(BidderExperience(
                    exp_id=row["exp_id"].strip(),
                    bidder_id=row["bidder_id"].strip(),
                    client_name=row["client_name"].strip(),
                    project_title=row["project_title"].strip(),
                    completion_date=row["completion_date"].strip(),
                    contract_value=to_decimal(row["contract_value"]),
                    scope_summary=row.get("scope_summary", "").strip(),
                    certificate_reference=row.get("certificate_reference", "").strip(),
                    created_at=now_iso()
                ))
        return exps

    @staticmethod
    def import_certificates(file_path: str) -> List[BidderCertificate]:
        p = Path(file_path)
        if not p.exists():
            return []
        certs = []
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                certs.append(BidderCertificate(
                    cert_id=row["cert_id"].strip(),
                    bidder_id=row["bidder_id"].strip(),
                    cert_type=row["cert_type"].strip().upper(),
                    registration_number=row["registration_number"].strip(),
                    issuing_authority=row.get("issuing_authority", "").strip(),
                    issue_date=row["issue_date"].strip(),
                    expiry_date=row.get("expiry_date", "").strip() or None,
                    local_content_percentage=to_decimal(row.get("local_content_percentage", "0.00")),
                    is_valid=row.get("is_valid", "1") in ("1", "True", "true", "yes"),
                    created_at=now_iso()
                ))
        return certs

    @staticmethod
    def import_emd_records(file_path: str, tender_id: Optional[str] = None) -> List[EMDRecord]:
        p = Path(file_path)
        if not p.exists():
            return []
        records = []
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                t_id = row["tender_id"].strip()
                if tender_id and t_id != tender_id:
                    continue
                records.append(EMDRecord(
                    emd_id=row["emd_id"].strip(),
                    tender_id=t_id,
                    bidder_id=row["bidder_id"].strip(),
                    exemption_claimed=row.get("exemption_claimed", "0") in ("1", "True", "true", "yes"),
                    exemption_category=row.get("exemption_category", "").strip().upper() or None,
                    payment_mode=row.get("payment_mode", "BG").strip().upper() or None,
                    amount_paid=to_decimal(row.get("amount_paid", "0.00")),
                    instrument_reference=row.get("instrument_reference", "").strip() or None,
                    instrument_date=row.get("instrument_date", "").strip() or None,
                    valid_until=row.get("valid_until", "").strip() or None,
                    bank_name=row.get("bank_name", "").strip() or None,
                    status="PENDING",
                    created_at=now_iso()
                ))
        return records

    @staticmethod
    def import_technical_scores(file_path: str) -> List[Dict[str, Any]]:
        p = Path(file_path)
        if not p.exists():
            return []
        scores = []
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores.append({
                    "score_id": row["score_id"].strip(),
                    "bid_id": row["bid_id"].strip(),
                    "criterion_code": row["criterion_code"].strip(),
                    "evaluator_id": row["evaluator_id"].strip(),
                    "raw_score": to_decimal(row["raw_score"]),
                    "remarks": row.get("remarks", "").strip()
                })
        return scores

    @staticmethod
    def import_price_schedules(file_path: str) -> List[PriceScheduleItem]:
        p = Path(file_path)
        if not p.exists():
            return []
        items = []
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(PriceScheduleItem(
                    schedule_id=row["schedule_id"].strip(),
                    bid_id=row["bid_id"].strip(),
                    item_no=int(row["item_no"]),
                    description=row["description"].strip(),
                    quantity=to_decimal(row["quantity"]),
                    unit=row["unit"].strip(),
                    quoted_unit_rate=to_decimal(row["quoted_unit_rate"]),
                    quoted_total_amount=to_decimal(row["quoted_total_amount"]),
                    is_gst_included=row.get("is_gst_included", "1") in ("1", "True", "true", "yes"),
                    gst_rate_pct=to_decimal(row.get("gst_rate_pct", "18.00")),
                    is_freight_included=row.get("is_freight_included", "1") in ("1", "True", "true", "yes"),
                    freight_amount=to_decimal(row.get("freight_amount", "0.00")),
                    created_at=now_iso()
                ))
        return items
