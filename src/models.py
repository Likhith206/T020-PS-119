"""
TENDERLENS — Unified Domain Models
Represents core entities for the explainable procurement evaluation engine.
All financial fields maintain string or Decimal representations to prevent precision loss.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, List, Dict, Any
from src.utils.money_utils import to_decimal, quantize_money, quantize_percent


@dataclass
class Tender:
    tender_id: str
    title: str
    description: str
    estimated_cost: Decimal
    currency: str = "INR"
    bid_opening_date: str = ""
    bid_closing_date: str = ""
    bid_validity_days: int = 90
    evaluation_method: str = "LCS"  # LCS or QCBS
    qcbs_tech_weight: Decimal = Decimal("70.00")
    qcbs_fin_weight: Decimal = Decimal("30.00")
    emd_required: bool = True
    emd_amount: Decimal = Decimal("0.00")
    mse_relax_enabled: bool = False
    single_bid_allowed: bool = False
    is_reserved_item: bool = False
    status: str = "CREATED"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        self.estimated_cost = to_decimal(self.estimated_cost)
        self.qcbs_tech_weight = to_decimal(self.qcbs_tech_weight)
        self.qcbs_fin_weight = to_decimal(self.qcbs_fin_weight)
        self.emd_amount = to_decimal(self.emd_amount)


@dataclass
class Bidder:
    bidder_id: str
    name: str
    organization_type: str
    registration_no: Optional[str] = None
    pan_no: Optional[str] = None
    gstin: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    registered_address: Optional[str] = None
    is_blacklisted: bool = False
    blacklisted_since: Optional[str] = None
    blacklisting_reason: Optional[str] = None
    created_at: str = ""


@dataclass
class Bid:
    bid_id: str
    tender_id: str
    bidder_id: str
    submission_timestamp: str
    technical_envelope_opened: bool = False
    financial_envelope_opened: bool = False
    responsiveness_status: str = "SUBMITTED"
    technical_status: str = "PENDING"
    overall_technical_score: Decimal = Decimal("0.00")
    financial_status: str = "LOCKED"
    final_rank: Optional[int] = None
    final_award_status: str = "NONE"
    created_at: str = ""

    def __post_init__(self):
        self.overall_technical_score = to_decimal(self.overall_technical_score)


@dataclass
class BidderExperience:
    exp_id: str
    bidder_id: str
    client_name: str
    project_title: str
    completion_date: str
    contract_value: Decimal
    scope_summary: Optional[str] = None
    certificate_reference: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        self.contract_value = to_decimal(self.contract_value)


@dataclass
class BidderCertificate:
    cert_id: str
    bidder_id: str
    cert_type: str  # MSE, STARTUP, MAKE_IN_INDIA, ISO
    registration_number: str
    issuing_authority: Optional[str] = None
    issue_date: str = ""
    expiry_date: Optional[str] = None
    local_content_percentage: Decimal = Decimal("0.00")
    is_valid: bool = True
    created_at: str = ""

    def __post_init__(self):
        self.local_content_percentage = to_decimal(self.local_content_percentage)


@dataclass
class EMDRecord:
    emd_id: str
    tender_id: str
    bidder_id: str
    exemption_claimed: bool = False
    exemption_category: Optional[str] = None
    payment_mode: Optional[str] = None  # BG, DD, ONLINE, EXEMPT
    amount_paid: Decimal = Decimal("0.00")
    instrument_reference: Optional[str] = None
    instrument_date: Optional[str] = None
    valid_until: Optional[str] = None
    bank_name: Optional[str] = None
    status: str = "PENDING"
    forfeiture_reason: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        self.amount_paid = to_decimal(self.amount_paid)


@dataclass
class TechnicalCriterion:
    criterion_id: str
    tender_id: str
    code: str
    name: str
    weight_pct: Decimal
    min_score_pct: Decimal = Decimal("60.00")
    description: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        self.weight_pct = to_decimal(self.weight_pct)
        self.min_score_pct = to_decimal(self.min_score_pct)


@dataclass
class TechnicalScore:
    score_id: str
    bid_id: str
    criterion_id: str
    evaluator_id: str
    raw_score: Decimal
    remarks: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        self.raw_score = to_decimal(self.raw_score)


@dataclass
class PriceScheduleItem:
    schedule_id: str
    bid_id: str
    item_no: int
    description: str
    quantity: Decimal
    unit: str
    quoted_unit_rate: Decimal
    quoted_total_amount: Decimal
    is_gst_included: bool = True
    gst_rate_pct: Decimal = Decimal("18.00")
    is_freight_included: bool = True
    freight_amount: Decimal = Decimal("0.00")
    created_at: str = ""

    def __post_init__(self):
        self.quantity = to_decimal(self.quantity)
        self.quoted_unit_rate = to_decimal(self.quoted_unit_rate)
        self.quoted_total_amount = to_decimal(self.quoted_total_amount)
        self.gst_rate_pct = to_decimal(self.gst_rate_pct)
        self.freight_amount = to_decimal(self.freight_amount)


@dataclass
class FinancialEvaluation:
    eval_id: str
    bid_id: str
    original_quoted_total: Decimal
    arithmetic_corrected_total: Decimal
    has_arithmetic_discrepancy: bool
    arithmetic_discrepancy_details: Optional[str]
    correction_accepted: bool
    base_tax_adjusted_total: Decimal
    freight_adjusted_total: Decimal
    final_comparative_price: Decimal
    financial_score: Optional[Decimal] = None
    combined_qcbs_score: Optional[Decimal] = None
    is_abnormally_low: bool = False
    abnormal_justification_status: Optional[str] = None
    additional_security_required: Decimal = Decimal("0.00")
    evaluated_at: str = ""

    def __post_init__(self):
        self.original_quoted_total = to_decimal(self.original_quoted_total)
        self.arithmetic_corrected_total = to_decimal(self.arithmetic_corrected_total)
        self.base_tax_adjusted_total = to_decimal(self.base_tax_adjusted_total)
        self.freight_adjusted_total = to_decimal(self.freight_adjusted_total)
        self.final_comparative_price = to_decimal(self.final_comparative_price)
        if self.financial_score is not None:
            self.financial_score = to_decimal(self.financial_score)
        if self.combined_qcbs_score is not None:
            self.combined_qcbs_score = to_decimal(self.combined_qcbs_score)
        self.additional_security_required = to_decimal(self.additional_security_required)


@dataclass
class PreferenceAllocation:
    allocation_id: str
    tender_id: str
    bidder_id: str
    preference_type: str  # NONE, MSE, MAKE_IN_INDIA
    is_l1_matched: bool
    allocated_quantity_pct: Decimal
    awarded_price: Decimal
    rationale: str
    created_at: str = ""

    def __post_init__(self):
        self.allocated_quantity_pct = to_decimal(self.allocated_quantity_pct)
        self.awarded_price = to_decimal(self.awarded_price)


@dataclass
class DecisionRecord:
    decision_id: str
    tender_id: str
    bidder_id: Optional[str]
    rule_id: str
    evaluation_stage: str
    input_values: Dict[str, Any]
    required_thresholds: Dict[str, Any]
    calculation_details: str
    result: str  # PASS, FAIL, WARNING, BLOCKED, SKIPPED
    human_explanation: str
    evidence_reference: Optional[str] = None
    created_at: str = ""


@dataclass
class GraphNode:
    node_id: str
    tender_id: str
    bidder_id: Optional[str]
    stage_name: str
    stage_order: int
    business_rule_ids: List[str]
    execution_status: str  # PENDING, RUNNING, PASSED, FAILED, WARNING, BLOCKED, SKIPPED
    input_snapshot: Dict[str, Any] = field(default_factory=dict)
    output_snapshot: Dict[str, Any] = field(default_factory=dict)
    calculation_details: str = ""
    decision_explanation: str = ""
    evidence_reference: str = ""
    execution_timestamp: str = ""
    is_simulation: bool = False
    simulation_id: Optional[str] = None


@dataclass
class GraphEdge:
    edge_id: str
    tender_id: str
    source_node_id: str
    target_node_id: str
    dependency_condition: str
    dependency_result: str  # SATISFIED, UNSATISFIED, BLOCKED
    explanation: str
    is_simulation: bool = False
    simulation_id: Optional[str] = None


@dataclass
class AuditEvent:
    event_id: str
    tender_id: str
    sequence_no: int
    event_type: str
    event_details: Dict[str, Any]
    previous_hash: str
    current_hash: str
    timestamp: str
    bidder_id: Optional[str] = None


@dataclass
class RiskRecord:
    risk_id: str
    tender_id: str
    risk_category: str  # COMPLIANCE, FINANCIAL, TECHNICAL, TIMELINE, INTEGRITY
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    triggering_condition: str
    evidence: str
    explanation: str
    suggested_action: str
    detected_at: str
    bidder_id: Optional[str] = None


@dataclass
class Award:
    award_id: str
    tender_id: str
    awarded_bidder_id: str
    contract_value: Decimal
    award_method: str
    loa_reference: str
    loa_issue_date: str
    security_due_date: str
    status: str = "LOA_ISSUED"
    created_at: str = ""

    def __post_init__(self):
        self.contract_value = to_decimal(self.contract_value)


@dataclass
class PerformanceSecurity:
    security_id: str
    award_id: str
    standard_security_rate_pct: Decimal
    standard_security_amount: Decimal
    additional_security_amount: Decimal
    total_security_required: Decimal
    submitted_amount: Decimal = Decimal("0.00")
    instrument_type: Optional[str] = None
    instrument_ref: Optional[str] = None
    valid_until: Optional[str] = None
    submission_date: Optional[str] = None
    is_verified: bool = False
    status: str = "PENDING"
    created_at: str = ""

    def __post_init__(self):
        self.standard_security_rate_pct = to_decimal(self.standard_security_rate_pct)
        self.standard_security_amount = to_decimal(self.standard_security_amount)
        self.additional_security_amount = to_decimal(self.additional_security_amount)
        self.total_security_required = to_decimal(self.total_security_required)
        self.submitted_amount = to_decimal(self.submitted_amount)
