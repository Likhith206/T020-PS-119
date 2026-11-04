"""
TENDERLENS — Master Evaluation Pipeline & Orchestrator (BR-12)
Enforces the mandatory 9-stage evaluation sequence, strict two-envelope logical isolation,
Decision Graph generation, explainable decision recording, and hash-linked audit logging.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from src.models import Tender, Bid, Bidder, DecisionRecord
from src.storage.database import Database
from src.storage.repositories import (
    TenderRepository, BidderRepository, BidRepository, EMDRepository,
    TechnicalRepository, FinancialRepository, PreferenceRepository,
    DecisionRepository, AwardRepository
)
from src.core.decision_graph import ProcurementDecisionGraph
from src.engines.emd_engine import EMDEngine
from src.engines.eligibility_engine import EligibilityEngine
from src.engines.technical_engine import TechnicalEngine
from src.engines.financial_engine import FinancialEngine, TwoEnvelopeViolationError
from src.engines.abnormal_bid_engine import AbnormalBidEngine
from src.engines.preference_engine import PreferenceEngine
from src.engines.ranking_engine import RankingEngine
from src.engines.validity_engine import ValidityEngine
from src.engines.award_engine import AwardEngine
from src.engines.single_bid_engine import SingleBidEngine
from src.engines.negotiation_engine import NegotiationEngine
from src.intelligence.audit_engine import AuditEngine
from src.intelligence.risk_analyzer import RiskAnalyzer
from src.utils.validators import validate_config_files
from src.utils.date_utils import now_iso
from src.utils.money_utils import format_inr


class ProcurementEvaluator:
    def __init__(self, db: Database, config_dir: str = "config"):
        self.db = db
        self.configs = validate_config_files(config_dir)
        self.rules_cfg = self.configs["business_rules"]
        self.scoring_cfg = self.configs["scoring_defaults"]

        # Repositories
        self.tender_repo = TenderRepository(db)
        self.bidder_repo = BidderRepository(db)
        self.bid_repo = BidRepository(db)
        self.emd_repo = EMDRepository(db)
        self.tech_repo = TechnicalRepository(db)
        self.fin_repo = FinancialRepository(db)
        self.pref_repo = PreferenceRepository(db)
        self.dec_repo = DecisionRepository(db)
        self.award_repo = AwardRepository(db)

        # Engines
        self.emd_engine = EMDEngine(self.rules_cfg)
        self.elig_engine = EligibilityEngine(self.rules_cfg)
        self.tech_engine = TechnicalEngine(self.rules_cfg)
        self.fin_engine = FinancialEngine(self.rules_cfg)
        self.abnormal_engine = AbnormalBidEngine(self.rules_cfg)
        self.pref_engine = PreferenceEngine(self.rules_cfg)
        self.rank_engine = RankingEngine(self.scoring_cfg)
        self.validity_engine = ValidityEngine(self.rules_cfg)
        self.award_engine = AwardEngine(self.rules_cfg)
        self.single_bid_engine = SingleBidEngine(self.rules_cfg)
        self.negotiation_engine = NegotiationEngine(self.rules_cfg)

        # Intelligence
        self.audit_engine = AuditEngine(db, genesis_hash=self.configs["settings"]["audit_genesis_hash"])
        self.risk_analyzer = RiskAnalyzer(db)

    def evaluate_tender(self, tender_id: str) -> Dict[str, Any]:
        """
        Executes end-to-end evaluation for the specified tender in strict accordance with BR-12.
        """
        tender = self.tender_repo.get_by_id(tender_id)
        if not tender:
            raise ValueError(f"Tender {tender_id} not found.")

        self.audit_engine.log_event(
            tender_id=tender.tender_id,
            event_type="EVALUATION_STARTED",
            event_details={"tender_id": tender.tender_id, "estimated_cost": str(tender.estimated_cost)}
        )

        bids = self.bid_repo.list_by_tender(tender_id)
        criteria = self.tech_repo.list_criteria(tender_id)

        tender_graph = ProcurementDecisionGraph(tender.tender_id)
        bidder_graphs: Dict[str, ProcurementDecisionGraph] = {}

        # -------------------------------------------------------------------------
        # STAGE 1 & 2: TIMELINE, EMD & ELIGIBILITY (Per Bidder)
        # -------------------------------------------------------------------------
        responsive_bidders = []

        for bid in bids:
            b_graph = ProcurementDecisionGraph(tender.tender_id, bid.bidder_id)
            bidder_graphs[bid.bidder_id] = b_graph

            bidder = self.bidder_repo.get_by_id(bid.bidder_id)
            certs = self.bidder_repo.get_certificates_for_bidder(bid.bidder_id)
            exps = self.bidder_repo.get_experience_for_bidder(bid.bidder_id)
            emd = self.emd_repo.get_by_bidder(tender.tender_id, bid.bidder_id)

            # Node 1: EMD Evaluation
            emd_valid, emd_status, emd_dec = self.emd_engine.evaluate(tender, bidder, emd, certs)
            self.dec_repo.save(emd_dec)
            if emd:
                emd.status = emd_status
                self.emd_repo.save(emd)

            b_graph.update_node(
                "TIMELINE_AND_EMD",
                "PASSED" if emd_valid else "FAILED",
                emd_dec.human_explanation,
                calculation_details=emd_dec.calculation_details,
                evidence=emd_dec.evidence_reference or ""
            )

            if not emd_valid:
                bid.responsiveness_status = "NON_RESPONSIVE"
                self.bid_repo.save(bid)
                self.audit_engine.log_event(
                    tender.tender_id,
                    "EMD_FAILED",
                    {"bidder_id": bid.bidder_id, "reason": emd_dec.human_explanation},
                    bidder_id=bid.bidder_id
                )
                b_graph.persist(self.db)
                continue

            # Node 2: Eligibility Evaluation
            # Compute average turnover over experience records or default turnover proxy
            # If explicit turnover certificates/records exist, calculate average, else estimate from experiences
            if exps:
                avg_turnover = sum(e.contract_value for e in exps) / Decimal(max(1, len(exps)))
            else:
                avg_turnover = Decimal("0.00")

            elig_valid, elig_code, elig_decs = self.elig_engine.evaluate(
                tender, bidder, avg_turnover, exps, certs
            )
            for d in elig_decs:
                self.dec_repo.save(d)

            last_elig_dec = elig_decs[-1]
            b_graph.update_node(
                "ELIGIBILITY",
                "PASSED" if elig_valid else "FAILED",
                last_elig_dec.human_explanation,
                calculation_details=last_elig_dec.calculation_details,
                evidence=last_elig_dec.evidence_reference or ""
            )

            if not elig_valid:
                bid.responsiveness_status = "NON_RESPONSIVE"
                self.bid_repo.save(bid)
                self.audit_engine.log_event(
                    tender.tender_id,
                    "ELIGIBILITY_FAILED",
                    {"bidder_id": bid.bidder_id, "code": elig_code},
                    bidder_id=bid.bidder_id
                )
                b_graph.persist(self.db)
                continue

            bid.responsiveness_status = "RESPONSIVE"
            self.bid_repo.save(bid)
            responsive_bidders.append((bid, bidder, certs, b_graph))

        # -------------------------------------------------------------------------
        # STAGE 3: TECHNICAL EVALUATION (Two-Envelope Gate)
        # -------------------------------------------------------------------------
        technically_qualified = []

        for bid, bidder, certs, b_graph in responsive_bidders:
            bid.technical_envelope_opened = True
            scores = self.tech_repo.get_scores_for_bid(bid.bid_id)

            tech_pass, overall_score, crit_scores, tech_decs = self.tech_engine.evaluate(
                tender, bid, criteria, scores
            )
            for d in tech_decs:
                self.dec_repo.save(d)

            bid.overall_technical_score = overall_score
            bid.technical_status = "QUALIFIED" if tech_pass else "DISQUALIFIED"
            self.bid_repo.save(bid)

            last_tech_dec = tech_decs[-1]
            b_graph.update_node(
                "TECHNICAL_EVALUATION",
                "PASSED" if tech_pass else "FAILED",
                last_tech_dec.human_explanation,
                calculation_details=last_tech_dec.calculation_details,
                output_snapshot={"overall_score": str(overall_score)},
                evidence=last_tech_dec.evidence_reference or ""
            )

            self.audit_engine.log_event(
                tender.tender_id,
                "TECHNICAL_EVALUATED",
                {"bidder_id": bid.bidder_id, "score": str(overall_score), "status": bid.technical_status},
                bidder_id=bid.bidder_id
            )

            if not tech_pass:
                # Two-Envelope Guard: Disqualified bidder's financial envelope remains locked!
                bid.financial_envelope_opened = False
                bid.financial_status = "LOCKED"
                self.bid_repo.save(bid)
                b_graph.persist(self.db)
                continue

            technically_qualified.append((bid, bidder, certs, b_graph))

        # -------------------------------------------------------------------------
        # STAGE 4: FINANCIAL EVALUATION (Arithmetic corrections & normalization)
        # -------------------------------------------------------------------------
        financial_evals = []

        for bid, bidder, certs, b_graph in technically_qualified:
            # Unlock financial envelope now that technical qualification is verified
            bid.financial_envelope_opened = True
            bid.financial_status = "OPENED"
            self.bid_repo.save(bid)

            schedule_items = self.fin_repo.get_price_schedule(bid.bid_id)
            try:
                fin_eval, fin_decs = self.fin_engine.evaluate(tender, bid, schedule_items, correction_accepted=True)
                self.fin_repo.save_evaluation(fin_eval)
                for d in fin_decs:
                    self.dec_repo.save(d)

                b_graph.update_node(
                    "FINANCIAL_EVALUATION",
                    "PASSED",
                    f"Corrected & normalized financial price: {format_inr(fin_eval.final_comparative_price)}.",
                    calculation_details=fin_decs[0].calculation_details,
                    output_snapshot={"normalized_price": str(fin_eval.final_comparative_price)},
                    evidence="Normalized Comparative Financial Schedule"
                )

                self.audit_engine.log_event(
                    tender.tender_id,
                    "FINANCIAL_EVALUATED",
                    {"bidder_id": bid.bidder_id, "price": str(fin_eval.final_comparative_price)},
                    bidder_id=bid.bidder_id
                )
                financial_evals.append((bid, fin_eval, bidder, certs, b_graph))
            except TwoEnvelopeViolationError as err:
                b_graph.update_node("FINANCIAL_EVALUATION", "BLOCKED", str(err))
                b_graph.persist(self.db)

        # -------------------------------------------------------------------------
        # STAGE 5: ABNORMALLY LOW BID ANALYSIS (BR-07)
        # -------------------------------------------------------------------------
        commercially_viable = []
        raw_eval_list = [item[1] for item in financial_evals]

        for bid, fe, bidder, certs, b_graph in financial_evals:
            is_abnormal, is_accepted, add_sec, ab_dec = self.abnormal_engine.analyze_bid(
                tender, bid, fe, raw_eval_list, justification_status="ACCEPTED"
            )
            self.dec_repo.save(ab_dec)

            fe.is_abnormally_low = is_abnormal
            fe.abnormal_justification_status = "ACCEPTED" if is_accepted else "REJECTED"
            fe.additional_security_required = add_sec
            self.fin_repo.save_evaluation(fe)

            node_status = "PASSED" if not is_abnormal else ("WARNING" if is_accepted else "FAILED")
            b_graph.update_node(
                "ABNORMAL_BID_ANALYSIS",
                node_status,
                ab_dec.human_explanation,
                calculation_details=ab_dec.calculation_details,
                evidence=ab_dec.evidence_reference or ""
            )

            if is_accepted:
                commercially_viable.append((bid, fe, bidder, certs, b_graph))
            else:
                bid.financial_status = "REJECTED"
                self.bid_repo.save(bid)
                b_graph.persist(self.db)

        # -------------------------------------------------------------------------
        # STAGE 6: PROCUREMENT PREFERENCES (BR-05)
        # -------------------------------------------------------------------------
        preference_allocations = []
        if commercially_viable:
            # Temporary L1 for preference comparison base
            temp_l1_item = min(commercially_viable, key=lambda x: x[1].final_comparative_price)
            temp_l1_bid, temp_l1_fe, _, _, _ = temp_l1_item
            others = [(b, fe, bdr, c) for b, fe, bdr, c, _ in commercially_viable if b.bid_id != temp_l1_bid.bid_id]

            allocs, pref_decs = self.pref_engine.evaluate_preferences(
                tender, temp_l1_bid, temp_l1_fe, others
            )
            for a in allocs:
                self.pref_repo.save(a)
            for d in pref_decs:
                self.dec_repo.save(d)
            preference_allocations = allocs

            for b, fe, bidder, certs, b_graph in commercially_viable:
                alloc_for_b = next((a for a in allocs if a.bidder_id == bidder.bidder_id), None)
                if alloc_for_b:
                    b_graph.update_node(
                        "PROCUREMENT_PREFERENCES",
                        "PASSED",
                        alloc_for_b.rationale,
                        output_snapshot={"allocated_qty_pct": str(alloc_for_b.allocated_quantity_pct)}
                    )
                else:
                    b_graph.update_node(
                        "PROCUREMENT_PREFERENCES",
                        "PASSED",
                        "No preferential purchase split applicable."
                    )

        # -------------------------------------------------------------------------
        # STAGE 7: RANKING & SINGLE BID SAFEGUARD (BR-06 & BR-10)
        # -------------------------------------------------------------------------
        # Competition assessment (BR-10)
        viable_bids = [item[0] for item in commercially_viable]
        can_proceed, comp_action, comp_dec = self.single_bid_engine.evaluate_competition(tender, viable_bids)
        self.dec_repo.save(comp_dec)

        if not can_proceed:
            tender.status = "RETENDER_TRIGGERED"
            self.tender_repo.save(tender)
            for _, _, _, _, b_graph in commercially_viable:
                b_graph.update_node("RANKING", "FAILED", comp_dec.human_explanation)
                b_graph.persist(self.db)
            self.audit_engine.log_event(
                tender.tender_id,
                "RETENDER_TRIGGERED",
                {"action": comp_action, "reason": comp_dec.human_explanation}
            )
            return {
                "tender_id": tender.tender_id,
                "status": "RETENDER_TRIGGERED",
                "message": comp_dec.human_explanation
            }

        # Rank bids
        eval_pairs = [(b, fe) for b, fe, _, _, _ in commercially_viable]
        ranked_bids, rank_decs = self.rank_engine.rank_bids(tender, eval_pairs)
        for d in rank_decs:
            self.dec_repo.save(d)

        for b, fe, rank_val in ranked_bids:
            self.bid_repo.save(b)
            self.fin_repo.save_evaluation(fe)
            bg = bidder_graphs.get(b.bidder_id)
            if bg:
                bg.update_node(
                    "RANKING",
                    "PASSED",
                    f"Assigned Rank {rank_val} ({tender.evaluation_method}).",
                    output_snapshot={"rank": rank_val}
                )

        # -------------------------------------------------------------------------
        # STAGE 8: BID VALIDITY (BR-08)
        # -------------------------------------------------------------------------
        valid_bidders_for_award = []
        for b, fe, rank_val in ranked_bids:
            bg = bidder_graphs.get(b.bidder_id)
            is_valid, v_status, v_expiry, v_dec = self.validity_engine.evaluate_validity(tender, b)
            self.dec_repo.save(v_dec)
            if bg:
                bg.update_node(
                    "BID_VALIDITY",
                    "PASSED" if is_valid else "FAILED",
                    v_dec.human_explanation,
                    calculation_details=v_dec.calculation_details
                )
            if is_valid:
                valid_bidders_for_award.append((b, fe, rank_val))

        # -------------------------------------------------------------------------
        # STAGE 9: AWARD & PERFORMANCE SECURITY (BR-09, BR-11)
        # -------------------------------------------------------------------------
        award_obj = None
        security_obj = None
        if valid_bidders_for_award:
            winning_bid, winning_fe, winning_rank = valid_bidders_for_award[0]
            award_obj, security_obj, aw_dec = self.award_engine.create_award(
                tender, winning_bid, winning_fe
            )
            self.award_repo.save_award(award_obj)
            self.award_repo.save_security(security_obj)
            self.dec_repo.save(aw_dec)

            tender.status = "AWARDED"
            self.tender_repo.save(tender)
            winning_bid.final_award_status = "AWARDED"
            self.bid_repo.save(winning_bid)

            # Check if negotiation is recommended under BR-11
            is_neg_rec, neg_action, max_p, neg_dec = self.negotiation_engine.evaluate_negotiation_eligibility(
                tender, winning_bid, winning_fe, is_l1=True
            )
            self.dec_repo.save(neg_dec)

            for b, fe, rank_val in ranked_bids:
                bg = bidder_graphs.get(b.bidder_id)
                if bg:
                    if b.bid_id == winning_bid.bid_id:
                        bg.update_node(
                            "AWARD_AND_SECURITY",
                            "PASSED",
                            aw_dec.human_explanation,
                            calculation_details=aw_dec.calculation_details,
                            output_snapshot={"award_id": award_obj.award_id, "loa_ref": award_obj.loa_reference}
                        )
                    else:
                        bg.update_node(
                            "AWARD_AND_SECURITY",
                            "SKIPPED",
                            f"Not awarded (Rank {rank_val})."
                        )
                    bg.persist(self.db)

            self.audit_engine.log_event(
                tender.tender_id,
                "CONTRACT_AWARDED",
                {
                    "award_id": award_obj.award_id,
                    "awarded_bidder": award_obj.awarded_bidder_id,
                    "contract_value": str(award_obj.contract_value),
                    "loa_reference": award_obj.loa_reference
                },
                bidder_id=winning_bid.bidder_id
            )

        # Run automated risk intelligence scan
        self.risk_analyzer.scan_risks(tender)

        return {
            "tender_id": tender.tender_id,
            "status": tender.status,
            "award": award_obj,
            "performance_security": security_obj,
            "ranked_bids": ranked_bids,
            "preference_allocations": preference_allocations
        }
