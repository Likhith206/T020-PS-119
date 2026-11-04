"""
TENDERLENS — Business Rule Engine & Registry
Central registry mapping rule identifiers BR-01 through BR-12 to their domain specifications,
precedence levels, and configurable parameters.
"""

from typing import Dict, Any, List

RULES_REGISTRY = {
    "BR-01": {
        "title": "Bidder Eligibility Verification",
        "description": "Verifies 30% average turnover over 3 FY, 7-year past experience, blacklisting status, and MSE relaxation.",
        "stage": "ELIGIBILITY",
        "precedence": 2
    },
    "BR-02": {
        "title": "Earnest Money Deposit (EMD) Validation",
        "description": "Validates 2% EMD (capped at ₹50 Lakhs), MSE/Startup exemptions, and 45-day BG validity horizon.",
        "stage": "TIMELINE_AND_EMD",
        "precedence": 1
    },
    "BR-03": {
        "title": "Technical Qualification & Cut-offs",
        "description": "Enforces 60% individual criterion score and 70% overall technical threshold while locking financial envelope.",
        "stage": "TECHNICAL_EVALUATION",
        "precedence": 3
    },
    "BR-04": {
        "title": "Financial Normalization & Arithmetic Corrections",
        "description": "Applies unit-rate precedence over totals, adds excluded GST/freight, and establishes binding normalized price.",
        "stage": "FINANCIAL_EVALUATION",
        "precedence": 4
    },
    "BR-05": {
        "title": "Public Procurement Preferences (MSE & Make in India)",
        "description": "Applies MSE 15% margin / 25% quantity split and Class-I 20% margin / 50% split with 100% reserved item handling.",
        "stage": "PROCUREMENT_PREFERENCES",
        "precedence": 6
    },
    "BR-06": {
        "title": "Competitive Bid Ranking (LCS & QCBS)",
        "description": "Determines L1 under Least Cost Selection or computes composite scores under Quality and Cost Based Selection.",
        "stage": "RANKING",
        "precedence": 7
    },
    "BR-07": {
        "title": "Abnormally Low Bid Analysis",
        "description": "Detects bids < 85% of estimate or < 80% of average; requires rate justification and additional performance security.",
        "stage": "ABNORMAL_BID_ANALYSIS",
        "precedence": 5
    },
    "BR-08": {
        "title": "Bid Validity and Extension Horizon",
        "description": "Tracks 90-day base validity, manages single 30-day extension, and guarantees penalty-free exit upon refusal.",
        "stage": "BID_VALIDITY",
        "precedence": 8
    },
    "BR-09": {
        "title": "Contract Award & Performance Security",
        "description": "Issues LoA, mandates 3% standard (or 5% abnormal) security within 21 days, and manages fallback or forfeiture.",
        "stage": "AWARD_AND_SECURITY",
        "precedence": 9
    },
    "BR-10": {
        "title": "Single Responsive Bid & Competition Safeguards",
        "description": "Restricts single-bid award unless explicitly authorized; otherwise triggers mandatory re-tender.",
        "stage": "RANKING",
        "precedence": 7
    },
    "BR-11": {
        "title": "Price Negotiation Protocol",
        "description": "Restricts negotiation strictly to L1 bidder when evaluated price exceeds estimated cost by more than 10%.",
        "stage": "AWARD_AND_SECURITY",
        "precedence": 9
    },
    "BR-12": {
        "title": "Pipeline Orchestration & Business Rule Precedence",
        "description": "Enforces mandatory sequential execution and blocks downstream stages immediately when an upstream stage fails.",
        "stage": "ORCHESTRATION",
        "precedence": 0
    }
}


def get_rule_info(rule_id: str) -> Dict[str, Any]:
    return RULES_REGISTRY.get(rule_id, {
        "title": "Unknown Rule",
        "description": "No specification registered.",
        "stage": "GENERAL",
        "precedence": 99
    })
