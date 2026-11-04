"""
TENDERLENS — Storage Repositories
Clean data access layer for all domain entities.
Ensures parameterized SQL queries and strict conversion between database strings and domain objects.
"""

import json
from decimal import Decimal
from typing import List, Optional, Dict, Any
from src.storage.database import Database
from src.models import (
    Tender, Bidder, Bid, BidderExperience, BidderCertificate, EMDRecord,
    TechnicalCriterion, TechnicalScore, PriceScheduleItem, FinancialEvaluation,
    PreferenceAllocation, DecisionRecord, GraphNode, GraphEdge, AuditEvent,
    RiskRecord, Award, PerformanceSecurity
)
from src.utils.money_utils import to_decimal


class TenderRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, tender: Tender) -> None:
        sql = """
        INSERT INTO tenders (
            tender_id, title, description, estimated_cost, currency,
            bid_opening_date, bid_closing_date, bid_validity_days,
            evaluation_method, qcbs_tech_weight, qcbs_fin_weight,
            emd_required, emd_amount, mse_relax_enabled, single_bid_allowed,
            is_reserved_item, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tender_id) DO UPDATE SET
            title=excluded.title, description=excluded.description,
            estimated_cost=excluded.estimated_cost, status=excluded.status,
            updated_at=excluded.updated_at
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                tender.tender_id, tender.title, tender.description,
                str(tender.estimated_cost), tender.currency,
                tender.bid_opening_date, tender.bid_closing_date,
                tender.bid_validity_days, tender.evaluation_method,
                str(tender.qcbs_tech_weight), str(tender.qcbs_fin_weight),
                1 if tender.emd_required else 0, str(tender.emd_amount),
                1 if tender.mse_relax_enabled else 0,
                1 if tender.single_bid_allowed else 0,
                1 if tender.is_reserved_item else 0,
                tender.status, tender.created_at, tender.updated_at
            ))

    def get_by_id(self, tender_id: str) -> Optional[Tender]:
        rows = self.db.execute_query("SELECT * FROM tenders WHERE tender_id = ?", (tender_id,))
        if not rows:
            return None
        r = rows[0]
        return Tender(
            tender_id=r["tender_id"],
            title=r["title"],
            description=r["description"],
            estimated_cost=to_decimal(r["estimated_cost"]),
            currency=r["currency"],
            bid_opening_date=r["bid_opening_date"],
            bid_closing_date=r["bid_closing_date"],
            bid_validity_days=r["bid_validity_days"],
            evaluation_method=r["evaluation_method"],
            qcbs_tech_weight=to_decimal(r["qcbs_tech_weight"]),
            qcbs_fin_weight=to_decimal(r["qcbs_fin_weight"]),
            emd_required=bool(r["emd_required"]),
            emd_amount=to_decimal(r["emd_amount"]),
            mse_relax_enabled=bool(r["mse_relax_enabled"]),
            single_bid_allowed=bool(r["single_bid_allowed"]),
            is_reserved_item=bool(r["is_reserved_item"]),
            status=r["status"],
            created_at=r["created_at"],
            updated_at=r["updated_at"]
        )

    def list_all(self) -> List[Tender]:
        rows = self.db.execute_query("SELECT * FROM tenders ORDER BY created_at DESC")
        return [
            Tender(
                tender_id=r["tender_id"],
                title=r["title"],
                description=r["description"],
                estimated_cost=to_decimal(r["estimated_cost"]),
                currency=r["currency"],
                bid_opening_date=r["bid_opening_date"],
                bid_closing_date=r["bid_closing_date"],
                bid_validity_days=r["bid_validity_days"],
                evaluation_method=r["evaluation_method"],
                qcbs_tech_weight=to_decimal(r["qcbs_tech_weight"]),
                qcbs_fin_weight=to_decimal(r["qcbs_fin_weight"]),
                emd_required=bool(r["emd_required"]),
                emd_amount=to_decimal(r["emd_amount"]),
                mse_relax_enabled=bool(r["mse_relax_enabled"]),
                single_bid_allowed=bool(r["single_bid_allowed"]),
                is_reserved_item=bool(r["is_reserved_item"]),
                status=r["status"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
            for r in rows
        ]


class BidderRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, bidder: Bidder) -> None:
        sql = """
        INSERT INTO bidders (
            bidder_id, name, organization_type, registration_no, pan_no,
            gstin, email, phone, registered_address, is_blacklisted,
            blacklisted_since, blacklisting_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bidder_id) DO UPDATE SET
            name=excluded.name, organization_type=excluded.organization_type,
            is_blacklisted=excluded.is_blacklisted, blacklisted_since=excluded.blacklisted_since,
            blacklisting_reason=excluded.blacklisting_reason
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                bidder.bidder_id, bidder.name, bidder.organization_type,
                bidder.registration_no, bidder.pan_no, bidder.gstin,
                bidder.email, bidder.phone, bidder.registered_address,
                1 if bidder.is_blacklisted else 0, bidder.blacklisted_since,
                bidder.blacklisting_reason, bidder.created_at
            ))

    def get_by_id(self, bidder_id: str) -> Optional[Bidder]:
        rows = self.db.execute_query("SELECT * FROM bidders WHERE bidder_id = ?", (bidder_id,))
        if not rows:
            return None
        r = rows[0]
        return Bidder(
            bidder_id=r["bidder_id"],
            name=r["name"],
            organization_type=r["organization_type"],
            registration_no=r["registration_no"],
            pan_no=r["pan_no"],
            gstin=r["gstin"],
            email=r["email"],
            phone=r["phone"],
            registered_address=r["registered_address"],
            is_blacklisted=bool(r["is_blacklisted"]),
            blacklisted_since=r["blacklisted_since"],
            blacklisting_reason=r["blacklisting_reason"],
            created_at=r["created_at"]
        )

    def add_experience(self, exp: BidderExperience) -> None:
        sql = """
        INSERT INTO bidder_experience (
            exp_id, bidder_id, client_name, project_title, completion_date,
            contract_value, scope_summary, certificate_reference, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exp_id) DO NOTHING
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                exp.exp_id, exp.bidder_id, exp.client_name, exp.project_title,
                exp.completion_date, str(exp.contract_value), exp.scope_summary,
                exp.certificate_reference, exp.created_at
            ))

    def get_experience_for_bidder(self, bidder_id: str) -> List[BidderExperience]:
        rows = self.db.execute_query("SELECT * FROM bidder_experience WHERE bidder_id = ?", (bidder_id,))
        return [
            BidderExperience(
                exp_id=r["exp_id"],
                bidder_id=r["bidder_id"],
                client_name=r["client_name"],
                project_title=r["project_title"],
                completion_date=r["completion_date"],
                contract_value=to_decimal(r["contract_value"]),
                scope_summary=r["scope_summary"],
                certificate_reference=r["certificate_reference"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def add_certificate(self, cert: BidderCertificate) -> None:
        sql = """
        INSERT INTO bidder_certificates (
            cert_id, bidder_id, cert_type, registration_number, issuing_authority,
            issue_date, expiry_date, local_content_percentage, is_valid, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cert_id) DO NOTHING
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                cert.cert_id, cert.bidder_id, cert.cert_type, cert.registration_number,
                cert.issuing_authority, cert.issue_date, cert.expiry_date,
                str(cert.local_content_percentage), 1 if cert.is_valid else 0,
                cert.created_at
            ))

    def get_certificates_for_bidder(self, bidder_id: str) -> List[BidderCertificate]:
        rows = self.db.execute_query("SELECT * FROM bidder_certificates WHERE bidder_id = ?", (bidder_id,))
        return [
            BidderCertificate(
                cert_id=r["cert_id"],
                bidder_id=r["bidder_id"],
                cert_type=r["cert_type"],
                registration_number=r["registration_number"],
                issuing_authority=r["issuing_authority"],
                issue_date=r["issue_date"],
                expiry_date=r["expiry_date"],
                local_content_percentage=to_decimal(r["local_content_percentage"]),
                is_valid=bool(r["is_valid"]),
                created_at=r["created_at"]
            )
            for r in rows
        ]


class BidRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, bid: Bid) -> None:
        sql = """
        INSERT INTO bids (
            bid_id, tender_id, bidder_id, submission_timestamp,
            technical_envelope_opened, financial_envelope_opened,
            responsiveness_status, technical_status, overall_technical_score,
            financial_status, final_rank, final_award_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bid_id) DO UPDATE SET
            technical_envelope_opened=excluded.technical_envelope_opened,
            financial_envelope_opened=excluded.financial_envelope_opened,
            responsiveness_status=excluded.responsiveness_status,
            technical_status=excluded.technical_status,
            overall_technical_score=excluded.overall_technical_score,
            financial_status=excluded.financial_status,
            final_rank=excluded.final_rank,
            final_award_status=excluded.final_award_status
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                bid.bid_id, bid.tender_id, bid.bidder_id, bid.submission_timestamp,
                1 if bid.technical_envelope_opened else 0,
                1 if bid.financial_envelope_opened else 0,
                bid.responsiveness_status, bid.technical_status,
                str(bid.overall_technical_score), bid.financial_status,
                bid.final_rank, bid.final_award_status, bid.created_at
            ))

    def get_by_id(self, bid_id: str) -> Optional[Bid]:
        rows = self.db.execute_query("SELECT * FROM bids WHERE bid_id = ?", (bid_id,))
        if not rows:
            return None
        r = rows[0]
        return self._row_to_bid(r)

    def get_by_tender_and_bidder(self, tender_id: str, bidder_id: str) -> Optional[Bid]:
        rows = self.db.execute_query(
            "SELECT * FROM bids WHERE tender_id = ? AND bidder_id = ?",
            (tender_id, bidder_id)
        )
        if not rows:
            return None
        return self._row_to_bid(rows[0])

    def list_by_tender(self, tender_id: str) -> List[Bid]:
        rows = self.db.execute_query(
            "SELECT * FROM bids WHERE tender_id = ? ORDER BY submission_timestamp ASC",
            (tender_id,)
        )
        return [self._row_to_bid(r) for r in rows]

    def _row_to_bid(self, r: dict) -> Bid:
        return Bid(
            bid_id=r["bid_id"],
            tender_id=r["tender_id"],
            bidder_id=r["bidder_id"],
            submission_timestamp=r["submission_timestamp"],
            technical_envelope_opened=bool(r["technical_envelope_opened"]),
            financial_envelope_opened=bool(r["financial_envelope_opened"]),
            responsiveness_status=r["responsiveness_status"],
            technical_status=r["technical_status"],
            overall_technical_score=to_decimal(r["overall_technical_score"]),
            financial_status=r["financial_status"],
            final_rank=r["final_rank"],
            final_award_status=r["final_award_status"],
            created_at=r["created_at"]
        )


class EMDRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, record: EMDRecord) -> None:
        sql = """
        INSERT INTO emd_records (
            emd_id, tender_id, bidder_id, exemption_claimed, exemption_category,
            payment_mode, amount_paid, instrument_reference, instrument_date,
            valid_until, bank_name, status, forfeiture_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tender_id, bidder_id) DO UPDATE SET
            exemption_claimed=excluded.exemption_claimed,
            exemption_category=excluded.exemption_category,
            payment_mode=excluded.payment_mode,
            amount_paid=excluded.amount_paid,
            instrument_reference=excluded.instrument_reference,
            valid_until=excluded.valid_until,
            status=excluded.status,
            forfeiture_reason=excluded.forfeiture_reason
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                record.emd_id, record.tender_id, record.bidder_id,
                1 if record.exemption_claimed else 0, record.exemption_category,
                record.payment_mode, str(record.amount_paid),
                record.instrument_reference, record.instrument_date,
                record.valid_until, record.bank_name, record.status,
                record.forfeiture_reason, record.created_at
            ))

    def get_by_bidder(self, tender_id: str, bidder_id: str) -> Optional[EMDRecord]:
        rows = self.db.execute_query(
            "SELECT * FROM emd_records WHERE tender_id = ? AND bidder_id = ?",
            (tender_id, bidder_id)
        )
        if not rows:
            return None
        r = rows[0]
        return EMDRecord(
            emd_id=r["emd_id"],
            tender_id=r["tender_id"],
            bidder_id=r["bidder_id"],
            exemption_claimed=bool(r["exemption_claimed"]),
            exemption_category=r["exemption_category"],
            payment_mode=r["payment_mode"],
            amount_paid=to_decimal(r["amount_paid"]),
            instrument_reference=r["instrument_reference"],
            instrument_date=r["instrument_date"],
            valid_until=r["valid_until"],
            bank_name=r["bank_name"],
            status=r["status"],
            forfeiture_reason=r["forfeiture_reason"],
            created_at=r["created_at"]
        )


class TechnicalRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_criterion(self, crit: TechnicalCriterion) -> None:
        sql = """
        INSERT INTO technical_criteria (
            criterion_id, tender_id, code, name, description, weight_pct, min_score_pct, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tender_id, code) DO UPDATE SET
            name=excluded.name, weight_pct=excluded.weight_pct, min_score_pct=excluded.min_score_pct
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                crit.criterion_id, crit.tender_id, crit.code, crit.name,
                crit.description, str(crit.weight_pct), str(crit.min_score_pct),
                crit.created_at
            ))

    def list_criteria(self, tender_id: str) -> List[TechnicalCriterion]:
        rows = self.db.execute_query(
            "SELECT * FROM technical_criteria WHERE tender_id = ? ORDER BY code ASC",
            (tender_id,)
        )
        return [
            TechnicalCriterion(
                criterion_id=r["criterion_id"],
                tender_id=r["tender_id"],
                code=r["code"],
                name=r["name"],
                weight_pct=to_decimal(r["weight_pct"]),
                min_score_pct=to_decimal(r["min_score_pct"]),
                description=r["description"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def save_score(self, score: TechnicalScore) -> None:
        sql = """
        INSERT INTO technical_scores (
            score_id, bid_id, criterion_id, evaluator_id, raw_score, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bid_id, criterion_id, evaluator_id) DO UPDATE SET
            raw_score=excluded.raw_score, remarks=excluded.remarks
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                score.score_id, score.bid_id, score.criterion_id,
                score.evaluator_id, str(score.raw_score), score.remarks,
                score.created_at
            ))

    def get_scores_for_bid(self, bid_id: str) -> List[TechnicalScore]:
        rows = self.db.execute_query("SELECT * FROM technical_scores WHERE bid_id = ?", (bid_id,))
        return [
            TechnicalScore(
                score_id=r["score_id"],
                bid_id=r["bid_id"],
                criterion_id=r["criterion_id"],
                evaluator_id=r["evaluator_id"],
                raw_score=to_decimal(r["raw_score"]),
                remarks=r["remarks"],
                created_at=r["created_at"]
            )
            for r in rows
        ]


class FinancialRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_price_schedule_item(self, item: PriceScheduleItem) -> None:
        sql = """
        INSERT INTO price_schedules (
            schedule_id, bid_id, item_no, description, quantity, unit,
            quoted_unit_rate, quoted_total_amount, is_gst_included,
            gst_rate_pct, is_freight_included, freight_amount, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bid_id, item_no) DO UPDATE SET
            quoted_unit_rate=excluded.quoted_unit_rate,
            quoted_total_amount=excluded.quoted_total_amount,
            is_gst_included=excluded.is_gst_included,
            gst_rate_pct=excluded.gst_rate_pct,
            is_freight_included=excluded.is_freight_included,
            freight_amount=excluded.freight_amount
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                item.schedule_id, item.bid_id, item.item_no, item.description,
                str(item.quantity), item.unit, str(item.quoted_unit_rate),
                str(item.quoted_total_amount), 1 if item.is_gst_included else 0,
                str(item.gst_rate_pct), 1 if item.is_freight_included else 0,
                str(item.freight_amount), item.created_at
            ))

    def get_price_schedule(self, bid_id: str) -> List[PriceScheduleItem]:
        rows = self.db.execute_query(
            "SELECT * FROM price_schedules WHERE bid_id = ? ORDER BY item_no ASC",
            (bid_id,)
        )
        return [
            PriceScheduleItem(
                schedule_id=r["schedule_id"],
                bid_id=r["bid_id"],
                item_no=r["item_no"],
                description=r["description"],
                quantity=to_decimal(r["quantity"]),
                unit=r["unit"],
                quoted_unit_rate=to_decimal(r["quoted_unit_rate"]),
                quoted_total_amount=to_decimal(r["quoted_total_amount"]),
                is_gst_included=bool(r["is_gst_included"]),
                gst_rate_pct=to_decimal(r["gst_rate_pct"]),
                is_freight_included=bool(r["is_freight_included"]),
                freight_amount=to_decimal(r["freight_amount"]),
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def save_evaluation(self, ev: FinancialEvaluation) -> None:
        sql = """
        INSERT INTO financial_evaluations (
            eval_id, bid_id, original_quoted_total, arithmetic_corrected_total,
            has_arithmetic_discrepancy, arithmetic_discrepancy_details,
            correction_accepted, base_tax_adjusted_total, freight_adjusted_total,
            final_comparative_price, financial_score, combined_qcbs_score,
            is_abnormally_low, abnormal_justification_status, additional_security_required,
            evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bid_id) DO UPDATE SET
            arithmetic_corrected_total=excluded.arithmetic_corrected_total,
            has_arithmetic_discrepancy=excluded.has_arithmetic_discrepancy,
            arithmetic_discrepancy_details=excluded.arithmetic_discrepancy_details,
            correction_accepted=excluded.correction_accepted,
            final_comparative_price=excluded.final_comparative_price,
            financial_score=excluded.financial_score,
            combined_qcbs_score=excluded.combined_qcbs_score,
            is_abnormally_low=excluded.is_abnormally_low,
            abnormal_justification_status=excluded.abnormal_justification_status,
            additional_security_required=excluded.additional_security_required,
            evaluated_at=excluded.evaluated_at
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                ev.eval_id, ev.bid_id, str(ev.original_quoted_total),
                str(ev.arithmetic_corrected_total), 1 if ev.has_arithmetic_discrepancy else 0,
                ev.arithmetic_discrepancy_details, 1 if ev.correction_accepted else 0,
                str(ev.base_tax_adjusted_total), str(ev.freight_adjusted_total),
                str(ev.final_comparative_price),
                str(ev.financial_score) if ev.financial_score is not None else None,
                str(ev.combined_qcbs_score) if ev.combined_qcbs_score is not None else None,
                1 if ev.is_abnormally_low else 0, ev.abnormal_justification_status,
                str(ev.additional_security_required), ev.evaluated_at
            ))

    def get_evaluation(self, bid_id: str) -> Optional[FinancialEvaluation]:
        rows = self.db.execute_query("SELECT * FROM financial_evaluations WHERE bid_id = ?", (bid_id,))
        if not rows:
            return None
        r = rows[0]
        return FinancialEvaluation(
            eval_id=r["eval_id"],
            bid_id=r["bid_id"],
            original_quoted_total=to_decimal(r["original_quoted_total"]),
            arithmetic_corrected_total=to_decimal(r["arithmetic_corrected_total"]),
            has_arithmetic_discrepancy=bool(r["has_arithmetic_discrepancy"]),
            arithmetic_discrepancy_details=r["arithmetic_discrepancy_details"],
            correction_accepted=bool(r["correction_accepted"]),
            base_tax_adjusted_total=to_decimal(r["base_tax_adjusted_total"]),
            freight_adjusted_total=to_decimal(r["freight_adjusted_total"]),
            final_comparative_price=to_decimal(r["final_comparative_price"]),
            financial_score=to_decimal(r["financial_score"]) if r["financial_score"] is not None else None,
            combined_qcbs_score=to_decimal(r["combined_qcbs_score"]) if r["combined_qcbs_score"] is not None else None,
            is_abnormally_low=bool(r["is_abnormally_low"]),
            abnormal_justification_status=r["abnormal_justification_status"],
            additional_security_required=to_decimal(r["additional_security_required"]),
            evaluated_at=r["evaluated_at"]
        )


class PreferenceRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, alloc: PreferenceAllocation) -> None:
        sql = """
        INSERT INTO preference_allocations (
            allocation_id, tender_id, bidder_id, preference_type, is_l1_matched,
            allocated_quantity_pct, awarded_price, rationale, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                alloc.allocation_id, alloc.tender_id, alloc.bidder_id,
                alloc.preference_type, 1 if alloc.is_l1_matched else 0,
                str(alloc.allocated_quantity_pct), str(alloc.awarded_price),
                alloc.rationale, alloc.created_at
            ))

    def list_by_tender(self, tender_id: str) -> List[PreferenceAllocation]:
        rows = self.db.execute_query(
            "SELECT * FROM preference_allocations WHERE tender_id = ?",
            (tender_id,)
        )
        return [
            PreferenceAllocation(
                allocation_id=r["allocation_id"],
                tender_id=r["tender_id"],
                bidder_id=r["bidder_id"],
                preference_type=r["preference_type"],
                is_l1_matched=bool(r["is_l1_matched"]),
                allocated_quantity_pct=to_decimal(r["allocated_quantity_pct"]),
                awarded_price=to_decimal(r["awarded_price"]),
                rationale=r["rationale"],
                created_at=r["created_at"]
            )
            for r in rows
        ]


class DecisionRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, dec: DecisionRecord) -> None:
        sql = """
        INSERT INTO decisions (
            decision_id, tender_id, bidder_id, rule_id, evaluation_stage,
            input_values, required_thresholds, calculation_details,
            result, human_explanation, evidence_reference, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                dec.decision_id, dec.tender_id, dec.bidder_id, dec.rule_id,
                dec.evaluation_stage, json.dumps(dec.input_values),
                json.dumps(dec.required_thresholds), dec.calculation_details,
                dec.result, dec.human_explanation, dec.evidence_reference,
                dec.created_at
            ))

    def list_by_bidder(self, tender_id: str, bidder_id: str) -> List[DecisionRecord]:
        rows = self.db.execute_query(
            "SELECT * FROM decisions WHERE tender_id = ? AND bidder_id = ? ORDER BY created_at ASC",
            (tender_id, bidder_id)
        )
        return [self._row_to_decision(r) for r in rows]

    def list_by_stage(self, tender_id: str, bidder_id: str, stage: str) -> List[DecisionRecord]:
        rows = self.db.execute_query(
            "SELECT * FROM decisions WHERE tender_id = ? AND bidder_id = ? AND LOWER(evaluation_stage) = LOWER(?)",
            (tender_id, bidder_id, stage)
        )
        return [self._row_to_decision(r) for r in rows]

    def _row_to_decision(self, r: dict) -> DecisionRecord:
        return DecisionRecord(
            decision_id=r["decision_id"],
            tender_id=r["tender_id"],
            bidder_id=r["bidder_id"],
            rule_id=r["rule_id"],
            evaluation_stage=r["evaluation_stage"],
            input_values=json.loads(r["input_values"]),
            required_thresholds=json.loads(r["required_thresholds"]),
            calculation_details=r["calculation_details"],
            result=r["result"],
            human_explanation=r["human_explanation"],
            evidence_reference=r["evidence_reference"],
            created_at=r["created_at"]
        )


class DecisionGraphRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_node(self, node: GraphNode) -> None:
        sql = """
        INSERT INTO decision_graph_nodes (
            node_id, tender_id, bidder_id, stage_name, stage_order,
            business_rule_ids, execution_status, input_snapshot, output_snapshot,
            calculation_details, decision_explanation, evidence_reference,
            execution_timestamp, is_simulation, simulation_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            execution_status=excluded.execution_status,
            output_snapshot=excluded.output_snapshot,
            calculation_details=excluded.calculation_details,
            decision_explanation=excluded.decision_explanation,
            execution_timestamp=excluded.execution_timestamp
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                node.node_id, node.tender_id, node.bidder_id, node.stage_name,
                node.stage_order, json.dumps(node.business_rule_ids),
                node.execution_status, json.dumps(node.input_snapshot),
                json.dumps(node.output_snapshot), node.calculation_details,
                node.decision_explanation, node.evidence_reference,
                node.execution_timestamp, 1 if node.is_simulation else 0,
                node.simulation_id
            ))

    def save_edge(self, edge: GraphEdge) -> None:
        sql = """
        INSERT INTO decision_graph_edges (
            edge_id, tender_id, source_node_id, target_node_id,
            dependency_condition, dependency_result, explanation,
            is_simulation, simulation_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(edge_id) DO UPDATE SET
            dependency_result=excluded.dependency_result,
            explanation=excluded.explanation
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                edge.edge_id, edge.tender_id, edge.source_node_id,
                edge.target_node_id, edge.dependency_condition,
                edge.dependency_result, edge.explanation,
                1 if edge.is_simulation else 0, edge.simulation_id
            ))

    def get_nodes(self, tender_id: str, bidder_id: Optional[str] = None, simulation_id: Optional[str] = None) -> List[GraphNode]:
        query = "SELECT * FROM decision_graph_nodes WHERE tender_id = ?"
        params = [tender_id]
        if bidder_id:
            query += " AND bidder_id = ?"
            params.append(bidder_id)
        if simulation_id:
            query += " AND is_simulation = 1 AND simulation_id = ?"
            params.append(simulation_id)
        else:
            query += " AND is_simulation = 0"
        query += " ORDER BY stage_order ASC"

        rows = self.db.execute_query(query, tuple(params))
        return [
            GraphNode(
                node_id=r["node_id"],
                tender_id=r["tender_id"],
                bidder_id=r["bidder_id"],
                stage_name=r["stage_name"],
                stage_order=r["stage_order"],
                business_rule_ids=json.loads(r["business_rule_ids"]),
                execution_status=r["execution_status"],
                input_snapshot=json.loads(r["input_snapshot"]) if r["input_snapshot"] else {},
                output_snapshot=json.loads(r["output_snapshot"]) if r["output_snapshot"] else {},
                calculation_details=r["calculation_details"] or "",
                decision_explanation=r["decision_explanation"] or "",
                evidence_reference=r["evidence_reference"] or "",
                execution_timestamp=r["execution_timestamp"],
                is_simulation=bool(r["is_simulation"]),
                simulation_id=r["simulation_id"]
            )
            for r in rows
        ]

    def get_edges(self, tender_id: str, simulation_id: Optional[str] = None) -> List[GraphEdge]:
        query = "SELECT * FROM decision_graph_edges WHERE tender_id = ?"
        params = [tender_id]
        if simulation_id:
            query += " AND is_simulation = 1 AND simulation_id = ?"
            params.append(simulation_id)
        else:
            query += " AND is_simulation = 0"

        rows = self.db.execute_query(query, tuple(params))
        return [
            GraphEdge(
                edge_id=r["edge_id"],
                tender_id=r["tender_id"],
                source_node_id=r["source_node_id"],
                target_node_id=r["target_node_id"],
                dependency_condition=r["dependency_condition"],
                dependency_result=r["dependency_result"],
                explanation=r["explanation"],
                is_simulation=bool(r["is_simulation"]),
                simulation_id=r["simulation_id"]
            )
            for r in rows
        ]


class AuditRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, event: AuditEvent) -> None:
        sql = """
        INSERT INTO audit_events (
            event_id, tender_id, bidder_id, sequence_no, event_type,
            event_details, previous_hash, current_hash, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                event.event_id, event.tender_id, event.bidder_id,
                event.sequence_no, event.event_type,
                json.dumps(event.event_details, sort_keys=True),
                event.previous_hash, event.current_hash, event.timestamp
            ))

    def list_by_tender(self, tender_id: str) -> List[AuditEvent]:
        rows = self.db.execute_query(
            "SELECT * FROM audit_events WHERE tender_id = ? ORDER BY sequence_no ASC",
            (tender_id,)
        )
        return [
            AuditEvent(
                event_id=r["event_id"],
                tender_id=r["tender_id"],
                bidder_id=r["bidder_id"],
                sequence_no=r["sequence_no"],
                event_type=r["event_type"],
                event_details=json.loads(r["event_details"]),
                previous_hash=r["previous_hash"],
                current_hash=r["current_hash"],
                timestamp=r["timestamp"]
            )
            for r in rows
        ]

    def get_last_event(self, tender_id: str) -> Optional[AuditEvent]:
        rows = self.db.execute_query(
            "SELECT * FROM audit_events WHERE tender_id = ? ORDER BY sequence_no DESC LIMIT 1",
            (tender_id,)
        )
        if not rows:
            return None
        r = rows[0]
        return AuditEvent(
            event_id=r["event_id"],
            tender_id=r["tender_id"],
            bidder_id=r["bidder_id"],
            sequence_no=r["sequence_no"],
            event_type=r["event_type"],
            event_details=json.loads(r["event_details"]),
            previous_hash=r["previous_hash"],
            current_hash=r["current_hash"],
            timestamp=r["timestamp"]
        )


class RiskRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, risk: RiskRecord) -> None:
        sql = """
        INSERT INTO risk_records (
            risk_id, tender_id, bidder_id, risk_category, severity,
            triggering_condition, evidence, explanation, suggested_action, detected_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                risk.risk_id, risk.tender_id, risk.bidder_id, risk.risk_category,
                risk.severity, risk.triggering_condition, risk.evidence,
                risk.explanation, risk.suggested_action, risk.detected_at
            ))

    def list_by_tender(self, tender_id: str) -> List[RiskRecord]:
        rows = self.db.execute_query(
            "SELECT * FROM risk_records WHERE tender_id = ? ORDER BY detected_at ASC",
            (tender_id,)
        )
        return [
            RiskRecord(
                risk_id=r["risk_id"],
                tender_id=r["tender_id"],
                bidder_id=r["bidder_id"],
                risk_category=r["risk_category"],
                severity=r["severity"],
                triggering_condition=r["triggering_condition"],
                evidence=r["evidence"],
                explanation=r["explanation"],
                suggested_action=r["suggested_action"],
                detected_at=r["detected_at"]
            )
            for r in rows
        ]


class AwardRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_award(self, award: Award) -> None:
        sql = """
        INSERT INTO awards (
            award_id, tender_id, awarded_bidder_id, contract_value, award_method,
            loa_reference, loa_issue_date, security_due_date, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tender_id) DO UPDATE SET
            awarded_bidder_id=excluded.awarded_bidder_id,
            contract_value=excluded.contract_value,
            status=excluded.status
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                award.award_id, award.tender_id, award.awarded_bidder_id,
                str(award.contract_value), award.award_method, award.loa_reference,
                award.loa_issue_date, award.security_due_date, award.status,
                award.created_at
            ))

    def get_by_tender(self, tender_id: str) -> Optional[Award]:
        rows = self.db.execute_query("SELECT * FROM awards WHERE tender_id = ?", (tender_id,))
        if not rows:
            return None
        r = rows[0]
        return Award(
            award_id=r["award_id"],
            tender_id=r["tender_id"],
            awarded_bidder_id=r["awarded_bidder_id"],
            contract_value=to_decimal(r["contract_value"]),
            award_method=r["award_method"],
            loa_reference=r["loa_reference"],
            loa_issue_date=r["loa_issue_date"],
            security_due_date=r["security_due_date"],
            status=r["status"],
            created_at=r["created_at"]
        )

    def save_security(self, sec: PerformanceSecurity) -> None:
        sql = """
        INSERT INTO performance_securities (
            security_id, award_id, standard_security_rate_pct, standard_security_amount,
            additional_security_amount, total_security_required, submitted_amount,
            instrument_type, instrument_ref, valid_until, submission_date, is_verified,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(award_id) DO UPDATE SET
            submitted_amount=excluded.submitted_amount,
            status=excluded.status,
            is_verified=excluded.is_verified
        """
        with self.db.transaction() as cur:
            cur.execute(sql, (
                sec.security_id, sec.award_id, str(sec.standard_security_rate_pct),
                str(sec.standard_security_amount), str(sec.additional_security_amount),
                str(sec.total_security_required), str(sec.submitted_amount),
                sec.instrument_type, sec.instrument_ref, sec.valid_until,
                sec.submission_date, 1 if sec.is_verified else 0, sec.status,
                sec.created_at
            ))

    def get_security_by_award(self, award_id: str) -> Optional[PerformanceSecurity]:
        rows = self.db.execute_query("SELECT * FROM performance_securities WHERE award_id = ?", (award_id,))
        if not rows:
            return None
        r = rows[0]
        return PerformanceSecurity(
            security_id=r["security_id"],
            award_id=r["award_id"],
            standard_security_rate_pct=to_decimal(r["standard_security_rate_pct"]),
            standard_security_amount=to_decimal(r["standard_security_amount"]),
            additional_security_amount=to_decimal(r["additional_security_amount"]),
            total_security_required=to_decimal(r["total_security_required"]),
            submitted_amount=to_decimal(r["submitted_amount"]),
            instrument_type=r["instrument_type"],
            instrument_ref=r["instrument_ref"],
            valid_until=r["valid_until"],
            submission_date=r["submission_date"],
            is_verified=bool(r["is_verified"]),
            status=r["status"],
            created_at=r["created_at"]
        )
