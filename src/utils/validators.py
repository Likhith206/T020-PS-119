"""
TENDERLENS — Validation Utilities
Validates system configuration, input payloads, CSV schemas, and procurement constraints.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List
from src.utils.money_utils import to_decimal
from src.utils.date_utils import parse_date


class ValidationError(Exception):
    """Raised when configuration, CSV data, or operational input fails validation."""
    pass


def validate_config_files(config_dir: str = "config") -> Dict[str, Any]:
    """
    Validates presence and correctness of configuration files.
    Ensures no silent fallbacks are used when configurations are invalid.
    """
    cfg_path = Path(config_dir)
    settings_file = cfg_path / "settings.json"
    rules_file = cfg_path / "business_rules.json"
    scoring_file = cfg_path / "scoring_defaults.json"

    for f in [settings_file, rules_file, scoring_file]:
        if not f.exists():
            raise ValidationError(f"Mandatory configuration file missing: {f.name}")

    try:
        with open(settings_file, "r", encoding="utf-8") as fp:
            settings = json.load(fp)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {settings_file.name}: {e}")

    try:
        with open(rules_file, "r", encoding="utf-8") as fp:
            rules = json.load(fp)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {rules_file.name}: {e}")

    try:
        with open(scoring_file, "r", encoding="utf-8") as fp:
            scoring = json.load(fp)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {scoring_file.name}: {e}")

    # Validate essential keys in rules
    for key in ["eligibility", "emd", "technical", "financial", "preferences", "abnormal_bid", "validity", "award"]:
        if key not in rules:
            raise ValidationError(f"Missing required section '{key}' in business_rules.json")

    # Validate scoring criteria sum to 100.00
    criteria = scoring.get("default_technical_criteria", [])
    total_weight = sum([to_decimal(c.get("weight_pct", "0")) for c in criteria])
    if total_weight != Decimal("100.00"):
        raise ValidationError(f"Technical criteria weights must sum to 100.00%, got {total_weight}%")

    return {
        "settings": settings,
        "business_rules": rules,
        "scoring_defaults": scoring
    }


def validate_tender_dict(data: Dict[str, Any]) -> None:
    """Validates tender dictionary fields."""
    required = ["tender_id", "title", "estimated_cost", "bid_opening_date", "bid_closing_date", "evaluation_method"]
    for r in required:
        if not data.get(r):
            raise ValidationError(f"Tender missing mandatory field: {r}")

    # Check method
    method = str(data["evaluation_method"]).upper()
    if method not in ("LCS", "QCBS"):
        raise ValidationError(f"Evaluation method must be 'LCS' or 'QCBS', got '{method}'")

    # Check estimated cost
    cost = to_decimal(data["estimated_cost"])
    if cost <= Decimal("0.00"):
        raise ValidationError(f"Estimated cost must be strictly positive, got {cost}")

    # Check dates
    open_date = parse_date(data["bid_opening_date"])
    close_date = parse_date(data["bid_closing_date"])
    if close_date < open_date:
        raise ValidationError("Bid closing date cannot be before bid opening date")


def validate_csv_columns(actual_cols: List[str], required_cols: List[str], context: str) -> None:
    """Checks whether all required columns are present in CSV headers."""
    missing = [col for col in required_cols if col not in actual_cols]
    if missing:
        raise ValidationError(f"CSV for {context} is missing required columns: {missing}")
