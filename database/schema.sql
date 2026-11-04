-- TENDERLENS SQLite Database Schema
-- Version: 1.0.0
-- Compliant with PS-119 Tender Bid Evaluation Engine specifications

PRAGMA foreign_keys = ON;

-- 1. Tenders table
CREATE TABLE IF NOT EXISTS tenders (
    tender_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    estimated_cost TEXT NOT NULL,          -- Decimal string representation
    currency TEXT NOT NULL DEFAULT 'INR',
    bid_opening_date TEXT NOT NULL,        -- ISO Date YYYY-MM-DD
    bid_closing_date TEXT NOT NULL,        -- ISO Date YYYY-MM-DD
    bid_validity_days INTEGER NOT NULL DEFAULT 90,
    evaluation_method TEXT NOT NULL CHECK(evaluation_method IN ('LCS', 'QCBS')),
    qcbs_tech_weight TEXT DEFAULT '70.00', -- Decimal string
    qcbs_fin_weight TEXT DEFAULT '30.00',  -- Decimal string
    emd_required INTEGER NOT NULL DEFAULT 1,
    emd_amount TEXT NOT NULL,              -- Decimal string (e.g. 2% capped at 50L)
    mse_relax_enabled INTEGER NOT NULL DEFAULT 0,
    single_bid_allowed INTEGER NOT NULL DEFAULT 0,
    is_reserved_item INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'CREATED' 
        CHECK(status IN ('CREATED', 'PUBLISHED', 'OPEN', 'EVALUATING', 'EVALUATED', 'AWARDED', 'RETENDER_TRIGGERED', 'CANCELLED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Bidders table
CREATE TABLE IF NOT EXISTS bidders (
    bidder_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    organization_type TEXT NOT NULL,       -- e.g. Private Limited, Partnership, LLP, PSU
    registration_no TEXT UNIQUE,
    pan_no TEXT,
    gstin TEXT,
    email TEXT,
    phone TEXT,
    registered_address TEXT,
    is_blacklisted INTEGER NOT NULL DEFAULT 0,
    blacklisted_since TEXT,
    blacklisting_reason TEXT,
    created_at TEXT NOT NULL
);

-- 3. Bids table (Logical envelope separation)
CREATE TABLE IF NOT EXISTS bids (
    bid_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    submission_timestamp TEXT NOT NULL,
    technical_envelope_opened INTEGER NOT NULL DEFAULT 0,
    financial_envelope_opened INTEGER NOT NULL DEFAULT 0, -- Strict two-envelope guard
    responsiveness_status TEXT NOT NULL DEFAULT 'SUBMITTED'
        CHECK(responsiveness_status IN ('SUBMITTED', 'RESPONSIVE', 'NON_RESPONSIVE', 'WITHDRAWN')),
    technical_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(technical_status IN ('PENDING', 'QUALIFIED', 'DISQUALIFIED')),
    overall_technical_score TEXT DEFAULT '0.00',
    financial_status TEXT NOT NULL DEFAULT 'LOCKED'
        CHECK(financial_status IN ('LOCKED', 'OPENED', 'EVALUATED', 'REJECTED')),
    final_rank INTEGER,
    final_award_status TEXT DEFAULT 'NONE'
        CHECK(final_award_status IN ('NONE', 'RECOMMENDED', 'AWARDED', 'REJECTED', 'EXITED')),
    created_at TEXT NOT NULL,
    UNIQUE(tender_id, bidder_id)
);

-- 4. Bidder Experience table
CREATE TABLE IF NOT EXISTS bidder_experience (
    exp_id TEXT PRIMARY KEY,
    bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    client_name TEXT NOT NULL,
    project_title TEXT NOT NULL,
    completion_date TEXT NOT NULL,
    contract_value TEXT NOT NULL,          -- Decimal string
    scope_summary TEXT,
    certificate_reference TEXT,
    created_at TEXT NOT NULL
);

-- 5. Bidder Certificates table
CREATE TABLE IF NOT EXISTS bidder_certificates (
    cert_id TEXT PRIMARY KEY,
    bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    cert_type TEXT NOT NULL CHECK(cert_type IN ('MSE', 'STARTUP', 'MAKE_IN_INDIA', 'ISO', 'OTHER')),
    registration_number TEXT NOT NULL,
    issuing_authority TEXT,
    issue_date TEXT NOT NULL,
    expiry_date TEXT,
    local_content_percentage TEXT DEFAULT '0.00', -- For Class-I / Class-II supplier
    is_valid INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 6. EMD Records table
CREATE TABLE IF NOT EXISTS emd_records (
    emd_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    exemption_claimed INTEGER NOT NULL DEFAULT 0,
    exemption_category TEXT CHECK(exemption_category IN (NULL, 'MSE', 'STARTUP')),
    payment_mode TEXT CHECK(payment_mode IN ('BG', 'DD', 'ONLINE', 'EXEMPT')),
    amount_paid TEXT DEFAULT '0.00',
    instrument_reference TEXT,
    instrument_date TEXT,
    valid_until TEXT,
    bank_name TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(status IN ('PENDING', 'VALID', 'INVALID', 'FORFEITED', 'RELEASED')),
    forfeiture_reason TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(tender_id, bidder_id)
);

-- 7. Technical Criteria table
CREATE TABLE IF NOT EXISTS technical_criteria (
    criterion_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    weight_pct TEXT NOT NULL,             -- Decimal string (sum should equal 100.00)
    min_score_pct TEXT NOT NULL DEFAULT '60.00',
    created_at TEXT NOT NULL,
    UNIQUE(tender_id, code)
);

-- 8. Technical Scores table
CREATE TABLE IF NOT EXISTS technical_scores (
    score_id TEXT PRIMARY KEY,
    bid_id TEXT NOT NULL REFERENCES bids(bid_id) ON DELETE CASCADE,
    criterion_id TEXT NOT NULL REFERENCES technical_criteria(criterion_id) ON DELETE CASCADE,
    evaluator_id TEXT NOT NULL,
    raw_score TEXT NOT NULL,              -- 0 to 100 decimal string
    remarks TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(bid_id, criterion_id, evaluator_id)
);

-- 9. Price Schedules table (Uncorrected submitted schedule)
CREATE TABLE IF NOT EXISTS price_schedules (
    schedule_id TEXT PRIMARY KEY,
    bid_id TEXT NOT NULL REFERENCES bids(bid_id) ON DELETE CASCADE,
    item_no INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity TEXT NOT NULL,
    unit TEXT NOT NULL,
    quoted_unit_rate TEXT NOT NULL,
    quoted_total_amount TEXT NOT NULL,     -- As submitted by bidder
    is_gst_included INTEGER NOT NULL DEFAULT 1,
    gst_rate_pct TEXT DEFAULT '18.00',
    is_freight_included INTEGER NOT NULL DEFAULT 1,
    freight_amount TEXT DEFAULT '0.00',
    created_at TEXT NOT NULL,
    UNIQUE(bid_id, item_no)
);

-- 10. Financial Evaluations table (Normalized & Arithmetically corrected)
CREATE TABLE IF NOT EXISTS financial_evaluations (
    eval_id TEXT PRIMARY KEY,
    bid_id TEXT NOT NULL UNIQUE REFERENCES bids(bid_id) ON DELETE CASCADE,
    original_quoted_total TEXT NOT NULL,
    arithmetic_corrected_total TEXT NOT NULL,
    has_arithmetic_discrepancy INTEGER NOT NULL DEFAULT 0,
    arithmetic_discrepancy_details TEXT,
    correction_accepted INTEGER DEFAULT 1,
    base_tax_adjusted_total TEXT NOT NULL,
    freight_adjusted_total TEXT NOT NULL,
    final_comparative_price TEXT NOT NULL, -- Normalized price on common footing
    financial_score TEXT,                  -- QCBS financial score (out of 100)
    combined_qcbs_score TEXT,              -- QCBS composite score
    is_abnormally_low INTEGER NOT NULL DEFAULT 0,
    abnormal_justification_status TEXT CHECK(abnormal_justification_status IN (NULL, 'PENDING', 'ACCEPTED', 'REJECTED')),
    additional_security_required TEXT DEFAULT '0.00',
    evaluated_at TEXT NOT NULL
);

-- 11. Preference Allocations table
CREATE TABLE IF NOT EXISTS preference_allocations (
    allocation_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    preference_type TEXT NOT NULL CHECK(preference_type IN ('NONE', 'MSE', 'MAKE_IN_INDIA')),
    is_l1_matched INTEGER NOT NULL DEFAULT 0,
    allocated_quantity_pct TEXT NOT NULL DEFAULT '0.00',
    awarded_price TEXT NOT NULL,
    rationale TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 12. Procurement Events table
CREATE TABLE IF NOT EXISTS procurement_events (
    event_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT REFERENCES bidders(bidder_id),
    stage_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_payload TEXT,                   -- JSON payload of event state
    triggered_by TEXT NOT NULL DEFAULT 'SYSTEM',
    timestamp TEXT NOT NULL
);

-- 13. Validity Extensions table
CREATE TABLE IF NOT EXISTS validity_extensions (
    extension_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    original_validity_date TEXT NOT NULL,
    extension_days_requested INTEGER NOT NULL DEFAULT 30,
    extended_validity_date TEXT NOT NULL,
    bidder_response TEXT NOT NULL CHECK(bidder_response IN ('PENDING', 'ACCEPTED', 'REJECTED')),
    decision_timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 14. Awards table
CREATE TABLE IF NOT EXISTS awards (
    award_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL UNIQUE REFERENCES tenders(tender_id) ON DELETE CASCADE,
    awarded_bidder_id TEXT NOT NULL REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    contract_value TEXT NOT NULL,
    award_method TEXT NOT NULL CHECK(award_method IN ('LCS', 'QCBS', 'PREFERENCE')),
    loa_reference TEXT NOT NULL,
    loa_issue_date TEXT NOT NULL,
    security_due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'LOA_ISSUED' 
        CHECK(status IN ('LOA_ISSUED', 'SECURITY_DEPOSITED', 'CONTRACT_SIGNED', 'DEFAULTED', 'CANCELLED')),
    created_at TEXT NOT NULL
);

-- 15. Performance Securities table
CREATE TABLE IF NOT EXISTS performance_securities (
    security_id TEXT PRIMARY KEY,
    award_id TEXT NOT NULL UNIQUE REFERENCES awards(award_id) ON DELETE CASCADE,
    standard_security_rate_pct TEXT NOT NULL DEFAULT '3.00',
    standard_security_amount TEXT NOT NULL,
    additional_security_amount TEXT NOT NULL DEFAULT '0.00',
    total_security_required TEXT NOT NULL,
    submitted_amount TEXT DEFAULT '0.00',
    instrument_type TEXT,
    instrument_ref TEXT,
    valid_until TEXT,
    submission_date TEXT,
    is_verified INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(status IN ('PENDING', 'SUBMITTED', 'ACCEPTED', 'EXPIRED', 'FORFEITED')),
    created_at TEXT NOT NULL
);

-- 16. Explainable Decisions table
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    evaluation_stage TEXT NOT NULL,
    input_values TEXT NOT NULL,            -- JSON snapshot of inputs
    required_thresholds TEXT NOT NULL,     -- JSON snapshot of thresholds
    calculation_details TEXT NOT NULL,     -- Step-by-step formula and execution
    result TEXT NOT NULL CHECK(result IN ('PASS', 'FAIL', 'WARNING', 'BLOCKED', 'SKIPPED')),
    human_explanation TEXT NOT NULL,
    evidence_reference TEXT,
    created_at TEXT NOT NULL
);

-- 17. Decision Graph Nodes table
CREATE TABLE IF NOT EXISTS decision_graph_nodes (
    node_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT REFERENCES bidders(bidder_id) ON DELETE CASCADE,
    stage_name TEXT NOT NULL,
    stage_order INTEGER NOT NULL,
    business_rule_ids TEXT NOT NULL,       -- Comma-separated or JSON list
    execution_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(execution_status IN ('PENDING', 'RUNNING', 'PASSED', 'FAILED', 'WARNING', 'BLOCKED', 'SKIPPED')),
    input_snapshot TEXT,                   -- JSON string
    output_snapshot TEXT,                  -- JSON string
    calculation_details TEXT,
    decision_explanation TEXT,
    evidence_reference TEXT,
    execution_timestamp TEXT NOT NULL,
    is_simulation INTEGER NOT NULL DEFAULT 0,
    simulation_id TEXT
);

-- 18. Decision Graph Edges table
CREATE TABLE IF NOT EXISTS decision_graph_edges (
    edge_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    source_node_id TEXT NOT NULL REFERENCES decision_graph_nodes(node_id) ON DELETE CASCADE,
    target_node_id TEXT NOT NULL REFERENCES decision_graph_nodes(node_id) ON DELETE CASCADE,
    dependency_condition TEXT NOT NULL,
    dependency_result TEXT NOT NULL CHECK(dependency_result IN ('SATISFIED', 'UNSATISFIED', 'BLOCKED')),
    explanation TEXT NOT NULL,
    is_simulation INTEGER NOT NULL DEFAULT 0,
    simulation_id TEXT
);

-- 19. Tamper-Evident Audit Events table
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT REFERENCES bidders(bidder_id),
    sequence_no INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_details TEXT NOT NULL,           -- Canonical JSON representation
    previous_hash TEXT NOT NULL,
    current_hash TEXT NOT NULL,            -- SHA256(previous_hash + canonical_event)
    timestamp TEXT NOT NULL,
    UNIQUE(tender_id, sequence_no)
);

-- 20. Simulations table (What-If Analysis)
CREATE TABLE IF NOT EXISTS simulations (
    simulation_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    scenario_type TEXT NOT NULL,
    parameters TEXT NOT NULL,              -- JSON configuration of what changed
    original_outcome TEXT NOT NULL,        -- JSON summary of original result
    simulated_outcome TEXT NOT NULL,       -- JSON summary of simulated result
    diff_summary TEXT NOT NULL,            -- Human and structural diff
    created_at TEXT NOT NULL
);

-- 21. Risk Records table
CREATE TABLE IF NOT EXISTS risk_records (
    risk_id TEXT PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,
    bidder_id TEXT REFERENCES bidders(bidder_id),
    risk_category TEXT NOT NULL,           -- COMPLIANCE, FINANCIAL, TECHNICAL, TIMELINE, INTEGRITY
    severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    triggering_condition TEXT NOT NULL,
    evidence TEXT NOT NULL,
    explanation TEXT NOT NULL,
    suggested_action TEXT NOT NULL,
    detected_at TEXT NOT NULL
);

-- Indexes for performance & relational integrity
CREATE INDEX IF NOT EXISTS idx_bids_tender ON bids(tender_id);
CREATE INDEX IF NOT EXISTS idx_bids_bidder ON bids(bidder_id);
CREATE INDEX IF NOT EXISTS idx_tech_scores_bid ON technical_scores(bid_id);
CREATE INDEX IF NOT EXISTS idx_price_sched_bid ON price_schedules(bid_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tender_bidder ON decisions(tender_id, bidder_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_tender ON decision_graph_nodes(tender_id, bidder_id);
CREATE INDEX IF NOT EXISTS idx_audit_tender ON audit_events(tender_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_risks_tender ON risk_records(tender_id);
