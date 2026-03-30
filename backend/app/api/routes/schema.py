"""Schema browsing API — serves mock HCM Benefits metadata."""

import copy
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter

from app.config import settings

router = APIRouter()

logger = logging.getLogger(__name__)

# ── Persistence paths ──────────────────────────────────────────────────
_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_METADATA_FILE = _DATA_DIR / "column_metadata.json"
_HISTORY_FILE = _DATA_DIR / "metadata_history.json"

# ── Version history store ──────────────────────────────────────────────
_METADATA_HISTORY: List[Dict] = []
_NEXT_VERSION: int = 1


def _ensure_data_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _save_metadata():
    """Persist current metadata to disk."""
    _ensure_data_dir()
    with open(_METADATA_FILE, "w") as f:
        json.dump(_COLUMN_METADATA, f, indent=2)


def _load_metadata():
    """Load persisted metadata from disk, overriding hardcoded defaults."""
    if _METADATA_FILE.exists():
        try:
            with open(_METADATA_FILE, "r") as f:
                saved = json.load(f)
            _COLUMN_METADATA.update(saved)
            logger.info("Loaded persisted metadata (%d columns)", len(saved))
        except Exception as e:
            logger.warning("Failed to load persisted metadata: %s", e)


def _save_history():
    """Persist history to disk."""
    _ensure_data_dir()
    with open(_HISTORY_FILE, "w") as f:
        json.dump(_METADATA_HISTORY, f, indent=2)


def _load_history():
    """Load persisted history from disk."""
    global _METADATA_HISTORY, _NEXT_VERSION
    if _HISTORY_FILE.exists():
        try:
            with open(_HISTORY_FILE, "r") as f:
                _METADATA_HISTORY = json.load(f)
            logger.info("Loaded %d history entries", len(_METADATA_HISTORY))
            # Derive next version from existing data
            max_ver = 0
            for h in _METADATA_HISTORY:
                v = h.get("version", 0)
                if v > max_ver:
                    max_ver = v
            _NEXT_VERSION = max_ver + 1
        except Exception as e:
            logger.warning("Failed to load history: %s", e)


def _allocate_version() -> int:
    """Allocate a new version number."""
    global _NEXT_VERSION
    v = _NEXT_VERSION
    _NEXT_VERSION += 1
    return v


def _record_change(table_name: str, column_name: str, field: str, old_value, new_value, source: str, version: int = 0):
    """Record a single field change in the version history."""
    _METADATA_HISTORY.append({
        "id": len(_METADATA_HISTORY) + 1,
        "timestamp": time.time(),
        "table_name": table_name,
        "column_name": column_name,
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "source": source,
        "version": version,
    })
    _save_history()


def _apply_field_update(key: str, table_name: str, column_name: str, field: str, value, source: str, version: int = 0):
    """Apply a single field update with history tracking."""
    existing = _COLUMN_METADATA.get(key, {})
    old_value = copy.deepcopy(existing.get(field))
    existing[field] = value
    _COLUMN_METADATA[key] = existing
    _record_change(table_name, column_name, field, old_value, value, source, version)


# ── Rich column metadata: business rules, formulas, sample values, lineage ──
# Keyed by "table_name.column_name"
_COLUMN_METADATA = {
    # ── clients ──
    "clients.client_id": {
        "business_name": "Client Identifier",
        "business_description": "Unique identifier assigned to each company/customer on the HCM platform. Generated at onboarding time and immutable across the lifecycle.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002", "CLI-003"],
        "formula": None,
        "business_rules": [
            "Auto-generated UUID-style identifier at client onboarding",
            "Cannot be changed after creation",
            "Referenced by all tenant-scoped tables",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "Direct copy from source"},
        "used_in_metrics": ["All multi-tenant reports require client_id filter"],
        "relationships": ["Parent key for: regions, salary_bands, benefit_plans, employees, departments, open_enrollment_events"],
    },
    "clients.client_name": {
        "business_name": "Company Name",
        "business_description": "The legal or DBA name of the client company as registered during onboarding.",
        "valid_values": None,
        "sample_values": ["Acme Corp", "TechStart Inc", "Global Manufacturing LLC"],
        "formula": None,
        "business_rules": [
            "Must be unique across the platform",
            "Updated if the company undergoes a name change or merger",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Daily", "transformation": "Trimmed, title-cased"},
        "used_in_metrics": ["Client-level dashboard headers", "Cross-client comparison reports"],
        "relationships": [],
    },
    "clients.industry": {
        "business_name": "Industry Vertical",
        "business_description": "The primary industry classification of the client company. Used for benchmarking and regulatory grouping.",
        "valid_values": ["Technology", "Healthcare", "Manufacturing", "Retail", "Financial Services", "Education", "Government", "Non-Profit"],
        "sample_values": ["Technology", "Healthcare", "Manufacturing"],
        "formula": None,
        "business_rules": [
            "Set at onboarding, can be updated by account management",
            "Used to drive industry-specific compliance rules (e.g., ACA for healthcare)",
        ],
        "lineage": {"source_system": "CRM / Salesforce", "load_frequency": "Weekly", "transformation": "Mapped from SIC/NAICS code to category"},
        "used_in_metrics": ["Benchmarking reports", "Industry-level enrollment trends"],
        "relationships": [],
    },
    "clients.is_active": {
        "business_name": "Active Client Flag",
        "business_description": "Indicates whether the client currently has an active contract. Inactive clients retain historical data but cannot create new plans or enrollments.",
        "valid_values": ["TRUE", "FALSE"],
        "sample_values": ["TRUE", "FALSE"],
        "formula": "CASE WHEN contract_end_date IS NULL OR contract_end_date > CURRENT_DATE THEN TRUE ELSE FALSE END",
        "business_rules": [
            "Set to FALSE when contract is terminated",
            "Historical data is preserved but no new transactions are allowed",
            "Must filter to is_active = TRUE for operational reports",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Daily", "transformation": "Derived from contract dates"},
        "used_in_metrics": ["Active client count", "Client churn rate"],
        "relationships": [],
    },
    # ── employees ──
    "employees.employee_id": {
        "business_name": "Employee Identifier",
        "business_description": "System-generated unique identifier for each employee record. Distinct from the human-readable employee_number.",
        "valid_values": None,
        "sample_values": ["EMP-10001", "EMP-10002", "EMP-10003"],
        "formula": None,
        "business_rules": [
            "Auto-generated at employee creation",
            "Immutable — never reused even if employee is terminated and rehired",
            "Rehired employees get a new employee_id",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "Direct copy"},
        "used_in_metrics": ["All employee-level metrics use this as the grain key"],
        "relationships": ["FK parent for: benefit_enrollments, dependents"],
    },
    "employees.is_benefits_eligible": {
        "business_name": "Benefits Eligibility Flag",
        "business_description": "Indicates whether the employee is currently eligible to enroll in benefit plans. Driven by employment type, tenure, and client-specific eligibility rules.",
        "valid_values": ["TRUE", "FALSE"],
        "sample_values": ["TRUE", "FALSE"],
        "formula": "CASE WHEN employment_type IN ('full_time', 'part_time') AND DATEDIFF(day, hire_date, CURRENT_DATE) >= min_tenure_days AND employment_status != 'terminated' THEN TRUE ELSE FALSE END",
        "business_rules": [
            "Full-time employees are eligible after meeting minimum tenure (typically 30-90 days depending on client)",
            "Part-time eligibility varies by client and plan_eligibility_rules",
            "Contractors are generally NOT benefits-eligible",
            "Terminated employees lose eligibility on their termination_date",
            "Employees on leave retain eligibility",
            "Recalculated nightly based on plan_eligibility_rules table",
        ],
        "lineage": {"source_system": "HCM Core + Eligibility Engine", "load_frequency": "Nightly batch", "transformation": "Derived from eligibility rules engine — see plan_eligibility_rules table"},
        "used_in_metrics": ["Enrollment Rate = COUNT(enrolled) / COUNT(is_benefits_eligible = TRUE)", "Eligible headcount", "Eligibility gap analysis"],
        "relationships": ["Driven by: plan_eligibility_rules.employment_type, plan_eligibility_rules.min_tenure_days"],
    },
    "employees.employment_status": {
        "business_name": "Employment Status",
        "business_description": "Current employment lifecycle status. Critical filter for most operational reports.",
        "valid_values": ["active", "terminated", "leave"],
        "sample_values": ["active", "terminated", "leave"],
        "formula": None,
        "business_rules": [
            "'active' — Currently employed and working",
            "'terminated' — Employment ended; termination_date is populated",
            "'leave' — On approved leave (FMLA, disability, personal); retains benefits eligibility",
            "Status transitions: active → leave → active (return) OR active → terminated",
            "Terminated employees cannot transition back to active (rehire creates new record)",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time event-driven", "transformation": "Direct mapping from HR transaction codes"},
        "used_in_metrics": ["Active headcount", "Attrition rate", "Leave utilization", "Benefits enrollment rate (denominator often filtered to active + leave)"],
        "relationships": [],
    },
    "employees.employment_type": {
        "business_name": "Employment Type",
        "business_description": "Classification of the employment arrangement. Drives benefits eligibility, plan access, and cost-sharing rules.",
        "valid_values": ["full_time", "part_time", "contractor"],
        "sample_values": ["full_time", "part_time", "contractor"],
        "formula": None,
        "business_rules": [
            "'full_time' — 30+ hours/week; eligible for all benefit plans",
            "'part_time' — <30 hours/week; eligibility varies by client rules",
            "'contractor' — 1099 workers; generally NOT benefits-eligible",
            "ACA mandate: employees averaging 30+ hrs/week MUST be offered coverage",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "Mapped from job classification codes"},
        "used_in_metrics": ["FTE headcount", "Contractor ratio", "ACA compliance reports"],
        "relationships": ["Referenced by: plan_eligibility_rules.employment_type"],
    },
    "employees.hire_date": {
        "business_name": "Hire Date",
        "business_description": "The date the employee's employment began. Used to calculate tenure for eligibility and vesting purposes.",
        "valid_values": None,
        "sample_values": ["2023-01-15", "2024-06-01", "2025-03-20"],
        "formula": None,
        "business_rules": [
            "For rehired employees, this reflects the most recent hire date",
            "Tenure = DATEDIFF(day, hire_date, CURRENT_DATE)",
            "Benefits waiting period starts from hire_date",
            "Original hire date (if different from rehire date) tracked in separate field",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "Direct copy"},
        "used_in_metrics": ["New hire enrollment rate", "Average tenure", "Benefits waiting period tracking"],
        "relationships": ["Used in: plan_eligibility_rules.min_tenure_days check"],
    },
    # ── benefit_plans ──
    "benefit_plans.plan_type": {
        "business_name": "Plan Type",
        "business_description": "Category of the benefit plan. Determines the type of coverage provided and applicable regulations.",
        "valid_values": ["medical", "dental", "vision", "life", "std", "ltd", "fsa", "hsa"],
        "sample_values": ["medical", "dental", "vision"],
        "formula": None,
        "business_rules": [
            "'medical' — Health insurance (PPO, HMO, HDHP); ACA-regulated",
            "'dental' — Dental coverage; typically separate from medical",
            "'vision' — Vision/eye care coverage",
            "'life' — Life insurance (basic + voluntary/supplemental)",
            "'std' — Short-term disability (typically 60-90 days)",
            "'ltd' — Long-term disability (beyond STD period)",
            "'fsa' — Flexible Spending Account (pre-tax, use-it-or-lose-it)",
            "'hsa' — Health Savings Account (pre-tax, rolls over; requires HDHP medical plan)",
            "A client may have multiple plans of the same type (e.g., PPO and HDHP medical)",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Plan year setup", "transformation": "Standardized from carrier plan codes"},
        "used_in_metrics": ["Enrollment by plan type", "Cost analysis by plan type", "Plan migration tracking"],
        "relationships": [],
    },
    "benefit_plans.plan_year": {
        "business_name": "Plan Year",
        "business_description": "The calendar or fiscal year to which this plan instance applies. Most clients align with calendar year (Jan 1 – Dec 31).",
        "valid_values": None,
        "sample_values": ["2024", "2025", "2026"],
        "formula": None,
        "business_rules": [
            "New plan records are created each year during open enrollment setup",
            "Historical plan years are retained with is_active = FALSE",
            "Plan year determines which eligibility rules, costs, and coverage levels apply",
            "Some clients use fiscal year (e.g., July 1 – June 30)",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct copy"},
        "used_in_metrics": ["Year-over-year enrollment comparison", "Plan cost trend analysis"],
        "relationships": ["Related to: open_enrollment_events.plan_year"],
    },
    # ── benefit_enrollments ──
    "benefit_enrollments.enrollment_status": {
        "business_name": "Enrollment Status",
        "business_description": "Current state of the employee's enrollment in a specific benefit plan. Critical for determining who is actually covered.",
        "valid_values": ["active", "terminated", "waived", "pending"],
        "sample_values": ["active", "terminated", "waived"],
        "formula": None,
        "business_rules": [
            "'active' — Employee is currently enrolled and covered under this plan",
            "'terminated' — Enrollment was ended (employee left, changed plans, or canceled)",
            "'waived' — Employee explicitly declined coverage for this plan type (important for ACA tracking)",
            "'pending' — Enrollment submitted but not yet effective (e.g., during OE before plan year starts)",
            "An employee can have at most ONE active enrollment per plan_type at a time",
            "Waived enrollments are important: they prove the employee was offered coverage (ACA safe harbor)",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time event-driven", "transformation": "Mapped from enrollment transaction codes"},
        "used_in_metrics": ["Enrollment Rate = COUNT(DISTINCT employee_id WHERE status='active') / COUNT(DISTINCT eligible employees)", "Waiver rate", "Pending enrollment backlog"],
        "relationships": [],
    },
    "benefit_enrollments.enrollment_source": {
        "business_name": "Enrollment Source",
        "business_description": "How the enrollment originated. Determines applicable rules and deadlines.",
        "valid_values": ["open_enrollment", "new_hire", "qualifying_event"],
        "sample_values": ["open_enrollment", "new_hire", "qualifying_event"],
        "formula": None,
        "business_rules": [
            "'open_enrollment' — Annual enrollment window; employee selected/changed plans",
            "'new_hire' — First enrollment within 30-day new hire eligibility window",
            "'qualifying_event' — Mid-year change due to life event (marriage, birth, loss of other coverage)",
            "Each source has different deadlines and plan change rules",
            "QE enrollments require supporting documentation",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "Derived from enrollment transaction type"},
        "used_in_metrics": ["Enrollment by source", "New hire enrollment completion rate", "QE frequency analysis"],
        "relationships": [],
    },
    "benefit_enrollments.effective_date": {
        "business_name": "Enrollment Effective Date",
        "business_description": "The date coverage under this plan begins for the employee.",
        "valid_values": None,
        "sample_values": ["2026-01-01", "2026-03-15", "2025-07-01"],
        "formula": None,
        "business_rules": [
            "For open_enrollment: typically Jan 1 of the new plan year",
            "For new_hire: hire_date + waiting period (0-90 days depending on client)",
            "For qualifying_event: event date or first of the following month",
            "Must be >= hire_date",
            "Used to determine active enrollment window: effective_date <= reference_date < termination_date",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "Direct copy with validation against rules"},
        "used_in_metrics": ["Point-in-time enrollment snapshots", "New enrollment volume by month"],
        "relationships": [],
    },
    # ── benefit_plan_options ──
    "benefit_plan_options.coverage_level": {
        "business_name": "Coverage Level / Tier",
        "business_description": "Who is covered under the enrollment — employee only or employee plus dependents.",
        "valid_values": ["employee_only", "employee_spouse", "employee_children", "family"],
        "sample_values": ["employee_only", "family", "employee_spouse"],
        "formula": None,
        "business_rules": [
            "'employee_only' — Just the employee; lowest cost tier",
            "'employee_spouse' — Employee + spouse/domestic partner",
            "'employee_children' — Employee + child(ren)",
            "'family' — Employee + spouse + children; highest cost tier",
            "Cost increases with tier level: employee_only < employee_spouse ≈ employee_children < family",
            "Coverage level must be consistent with dependents on the enrollment",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Plan year setup", "transformation": "Direct copy from carrier data"},
        "used_in_metrics": ["Coverage tier distribution", "Average employer cost by tier", "Family coverage adoption rate"],
        "relationships": ["Validated against: dependent_enrollments (dependents listed must match tier)"],
    },
    "benefit_plan_options.annual_employee_cost": {
        "business_name": "Annual Employee Premium Cost",
        "business_description": "The total annual amount the employee pays for this coverage option, typically deducted pre-tax from payroll.",
        "valid_values": None,
        "sample_values": ["1200.00", "3600.00", "7200.00"],
        "formula": "Monthly payroll deduction × 12 (for semi-monthly: deduction × 24 / 2; for biweekly: deduction × 26 / 2)",
        "business_rules": [
            "Pre-tax deduction under Section 125 cafeteria plan",
            "Varies by coverage level, plan type, and sometimes salary band",
            "Employer typically subsidizes 60-80% of total premium",
            "Total premium = annual_employee_cost + annual_employer_cost",
            "HSA-eligible HDHPs tend to have lower employee premiums but higher deductibles",
        ],
        "lineage": {"source_system": "Benefits Admin / Carrier rate tables", "load_frequency": "Annual (plan year setup)", "transformation": "Loaded from carrier rate sheets, validated against prior year for reasonableness"},
        "used_in_metrics": ["Employee cost burden analysis", "Total compensation calculation", "Plan affordability (ACA)"],
        "relationships": ["Paired with: annual_employer_cost to get total premium"],
    },
    "benefit_plan_options.annual_employer_cost": {
        "business_name": "Annual Employer Premium Cost",
        "business_description": "The total annual amount the employer pays for this coverage option. Key component of benefits expense budgeting.",
        "valid_values": None,
        "sample_values": ["4800.00", "9600.00", "18000.00"],
        "formula": "Total annual premium - annual_employee_cost",
        "business_rules": [
            "Employer contribution varies by client, plan, and coverage level",
            "ACA affordability test: employee self-only contribution must be ≤ 9.12% of household income (2025 threshold)",
            "Some employers use defined contribution model (flat $ amount regardless of plan)",
        ],
        "lineage": {"source_system": "Benefits Admin / Carrier rate tables", "load_frequency": "Annual", "transformation": "Calculated from total premium minus employee share"},
        "used_in_metrics": ["Per-employee-per-month (PEPM) cost", "Total benefits liability", "Employer cost trend YoY"],
        "relationships": ["Paired with: annual_employee_cost"],
    },
    # ── benefit_claims ──
    "benefit_claims.billed_amount": {
        "business_name": "Billed Amount",
        "business_description": "The amount charged by the healthcare provider for the service rendered. This is the 'sticker price' before insurance adjustments.",
        "valid_values": None,
        "sample_values": ["250.00", "1500.00", "45000.00"],
        "formula": None,
        "business_rules": [
            "Represents the provider's full charge for the service",
            "Typically higher than allowed_amount due to negotiated network discounts",
            "Out-of-network claims may have billed_amount = allowed_amount",
        ],
        "lineage": {"source_system": "Claims Processing / Carrier 835/837 files", "load_frequency": "Daily batch", "transformation": "Direct from EDI claim feed"},
        "used_in_metrics": ["Average billed vs. allowed discount rate", "High-cost claim identification"],
        "relationships": ["Compare with: allowed_amount, paid_amount, employee_responsibility"],
    },
    "benefit_claims.allowed_amount": {
        "business_name": "Allowed Amount",
        "business_description": "The maximum amount the plan will consider for payment, based on negotiated provider rates or UCR schedules.",
        "valid_values": None,
        "sample_values": ["200.00", "1200.00", "38000.00"],
        "formula": "MIN(billed_amount, negotiated_rate) — for in-network; UCR schedule — for out-of-network",
        "business_rules": [
            "In-network: based on contracted rate between carrier and provider",
            "Out-of-network: based on Usual, Customary, and Reasonable (UCR) schedule",
            "Difference between billed and allowed is the 'provider write-off' (in-network) or patient balance bill (out-of-network)",
            "Always: allowed_amount <= billed_amount",
        ],
        "lineage": {"source_system": "Claims Processing / Carrier", "load_frequency": "Daily batch", "transformation": "Calculated by claims adjudication engine"},
        "used_in_metrics": ["Network discount savings", "Claim cost analysis"],
        "relationships": ["paid_amount + employee_responsibility should ≈ allowed_amount"],
    },
    "benefit_claims.paid_amount": {
        "business_name": "Plan Paid Amount",
        "business_description": "The amount the insurance plan actually pays toward the claim after applying deductibles, copays, and coinsurance.",
        "valid_values": None,
        "sample_values": ["160.00", "960.00", "32000.00"],
        "formula": "allowed_amount - deductible_applied - copay - coinsurance (subject to out-of-pocket maximum)",
        "business_rules": [
            "Plan pays $0 until deductible is met (for deductible-based plans)",
            "After deductible: plan pays coinsurance % (typically 80/20 or 70/30)",
            "After OOP max is reached: plan pays 100%",
            "Preventive care: plan pays 100% (ACA mandate, no deductible)",
            "paid_amount + employee_responsibility = allowed_amount",
        ],
        "lineage": {"source_system": "Claims Adjudication Engine", "load_frequency": "Daily batch", "transformation": "Calculated after applying benefit plan rules"},
        "used_in_metrics": ["Total claims cost (employer/plan perspective)", "Loss ratio = paid_amount / premium collected", "PEPM claims cost"],
        "relationships": ["Inverse of: employee_responsibility"],
    },
    "benefit_claims.employee_responsibility": {
        "business_name": "Employee Out-of-Pocket Amount",
        "business_description": "The portion of the allowed amount the employee must pay, including deductible, copay, and coinsurance.",
        "valid_values": None,
        "sample_values": ["40.00", "240.00", "6000.00"],
        "formula": "allowed_amount - paid_amount = deductible_portion + copay + coinsurance_portion",
        "business_rules": [
            "Capped at the plan's out-of-pocket maximum (oop_max) per plan year",
            "Components: deductible portion + copay (fixed $) + coinsurance (% of remaining)",
            "Once employee hits oop_max for the year, employee_responsibility = $0",
            "Tracks toward deductible_amount and oop_max accumulators",
        ],
        "lineage": {"source_system": "Claims Adjudication Engine", "load_frequency": "Daily batch", "transformation": "Calculated: allowed_amount - paid_amount"},
        "used_in_metrics": ["Employee cost burden", "OOP max utilization rate", "Deductible met percentage"],
        "relationships": ["Capped by: benefit_plan_options.oop_max"],
    },
    "benefit_claims.claim_type": {
        "business_name": "Claim Type / Service Category",
        "business_description": "Classification of the healthcare service that generated the claim.",
        "valid_values": ["in_network", "out_of_network", "prescription", "preventive"],
        "sample_values": ["in_network", "preventive", "prescription"],
        "formula": None,
        "business_rules": [
            "'in_network' — Service from a contracted provider; lower cost-sharing",
            "'out_of_network' — Service from a non-contracted provider; higher cost-sharing, possible balance billing",
            "'prescription' — Pharmacy claims (Rx); separate formulary tiers",
            "'preventive' — ACA-mandated preventive services (covered 100%, no cost-sharing)",
            "Network status affects both allowed_amount and cost-sharing percentages",
        ],
        "lineage": {"source_system": "Claims Processing / Carrier EDI", "load_frequency": "Daily batch", "transformation": "Mapped from place-of-service and provider network codes"},
        "used_in_metrics": ["Network utilization rate", "Preventive care compliance", "Rx spend analysis"],
        "relationships": [],
    },
    "benefit_claims.claim_status": {
        "business_name": "Claim Processing Status",
        "business_description": "Current state in the claim lifecycle from submission to final resolution.",
        "valid_values": ["submitted", "processed", "denied", "appealed"],
        "sample_values": ["processed", "denied", "submitted"],
        "formula": None,
        "business_rules": [
            "'submitted' — Claim received but not yet adjudicated",
            "'processed' — Claim adjudicated and payment determined",
            "'denied' — Claim rejected (reasons: not covered, pre-auth missing, out-of-network with no OON benefits)",
            "'appealed' — Denied claim under review after member/provider appeal",
            "Only 'processed' claims should be included in cost/utilization metrics",
            "Average processing time: 14-30 days from submission",
        ],
        "lineage": {"source_system": "Claims Processing", "load_frequency": "Daily batch", "transformation": "Direct from carrier claim status field"},
        "used_in_metrics": ["Claim denial rate", "Appeal success rate", "Claims processing turnaround"],
        "relationships": [],
    },
    # ── plan_eligibility_rules ──
    "plan_eligibility_rules.min_tenure_days": {
        "business_name": "Minimum Tenure (Days)",
        "business_description": "The minimum number of days an employee must be employed before becoming eligible for this plan. Also called the 'waiting period'.",
        "valid_values": None,
        "sample_values": ["0", "30", "60", "90"],
        "formula": "Employee becomes eligible when DATEDIFF(day, employees.hire_date, CURRENT_DATE) >= min_tenure_days",
        "business_rules": [
            "Common values: 0 (immediate), 30, 60, or 90 days",
            "ACA maximum waiting period: 90 days for full-time employees",
            "Varies by client and plan type (e.g., medical may require 30 days, dental may be immediate)",
            "Nullable = no tenure requirement (immediate eligibility)",
            "Applied in conjunction with employment_type and region/salary_band rules",
        ],
        "lineage": {"source_system": "Benefits Admin / Plan configuration", "load_frequency": "Annual (plan year setup)", "transformation": "Direct from plan configuration"},
        "used_in_metrics": ["Waiting period compliance", "Time-to-eligibility analysis"],
        "relationships": ["Applied to: employees.hire_date to determine employees.is_benefits_eligible"],
    },
    "plan_eligibility_rules.is_default": {
        "business_name": "Default Eligibility Rule Flag",
        "business_description": "Indicates whether this rule is the default (catch-all) eligibility rule for a plan. Non-default rules target specific regions, salary bands, or employment types.",
        "valid_values": ["TRUE", "FALSE"],
        "sample_values": ["TRUE", "FALSE"],
        "formula": None,
        "business_rules": [
            "Each plan should have exactly ONE default rule (is_default = TRUE)",
            "Default rule applies when no more specific rule matches",
            "Specificity order: region + salary_band + employment_type > region + employment_type > employment_type only > default",
            "If multiple rules match, the most specific one wins",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct from plan configuration"},
        "used_in_metrics": ["Rule complexity audit", "Eligibility rule coverage analysis"],
        "relationships": [],
    },
    # ── open_enrollment_events ──
    "open_enrollment_events.open_enrollment_start": {
        "business_name": "Open Enrollment Window Start",
        "business_description": "The first date employees can make benefit elections for the upcoming plan year.",
        "valid_values": None,
        "sample_values": ["2025-11-01", "2025-10-15"],
        "formula": None,
        "business_rules": [
            "Typically 2-4 weeks before the new plan year starts",
            "Most common window: November for January 1 plan year start",
            "Elections made during OE take effect on the plan year start date",
            "Employees who don't make elections are typically auto-enrolled in their current plan (passive enrollment)",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct from OE calendar configuration"},
        "used_in_metrics": ["OE participation rate", "OE completion timeline"],
        "relationships": ["Paired with: open_enrollment_end"],
    },
    # ── dependents ──
    "dependents.relationship": {
        "business_name": "Dependent Relationship",
        "business_description": "The dependent's relationship to the employee. Determines eligibility for coverage and IRS tax treatment.",
        "valid_values": ["spouse", "child", "domestic_partner"],
        "sample_values": ["spouse", "child", "domestic_partner"],
        "formula": None,
        "business_rules": [
            "'spouse' — Legal spouse; eligible for all dependent coverages",
            "'child' — Biological, adopted, or step-child; covered until age 26 (ACA mandate for medical)",
            "'domestic_partner' — Recognized in some states; tax treatment varies (imputed income may apply)",
            "Child age-out: at age 26, child loses medical eligibility (dental/vision may differ)",
            "Disabled adult children may retain eligibility beyond age 26 with documentation",
        ],
        "lineage": {"source_system": "HCM Core / Benefits Admin", "load_frequency": "Real-time", "transformation": "Direct from HR record"},
        "used_in_metrics": ["Dependent coverage rate", "Average dependents per employee", "Age-out tracking"],
        "relationships": ["Drives: dependent_enrollments eligibility"],
    },
    # ── departments ──
    "departments.parent_department_id": {
        "business_name": "Parent Department (Hierarchy)",
        "business_description": "Self-referencing foreign key to build organizational hierarchy. NULL for top-level departments.",
        "valid_values": None,
        "sample_values": ["DEPT-001", "DEPT-002", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = top-level department (e.g., 'Engineering', 'Sales')",
            "Supports multi-level hierarchy (e.g., Engineering → Backend → API Team)",
            "Used for roll-up reporting (aggregate child department metrics to parent)",
            "Maximum depth typically 4-5 levels",
        ],
        "lineage": {"source_system": "HCM Core / Org Chart", "load_frequency": "Daily", "transformation": "Direct copy from org structure"},
        "used_in_metrics": ["Departmental enrollment roll-ups", "Org-level benefits cost allocation"],
        "relationships": ["Self-FK: departments.department_id"],
    },
    "departments.cost_center_code": {
        "business_name": "Cost Center Code",
        "business_description": "Financial code used to allocate benefits expenses to the appropriate budget unit.",
        "valid_values": None,
        "sample_values": ["CC-1001", "CC-2050", "CC-3100"],
        "formula": None,
        "business_rules": [
            "Mapped to General Ledger accounts for financial reporting",
            "One department = one cost center (typically)",
            "Used for employer cost allocation: employer premium contributions charged to department's cost center",
            "Required for benefits expense accruals and journal entries",
        ],
        "lineage": {"source_system": "Finance / ERP", "load_frequency": "Monthly", "transformation": "Mapped from GL account structure"},
        "used_in_metrics": ["Benefits cost by cost center", "Budget vs. actual benefits spend"],
        "relationships": [],
    },
    # ── clients (remaining) ──
    "clients.country_code": {
        "business_name": "Client Country Code",
        "business_description": "ISO 3166-1 alpha-2 country code for the client company's primary domicile. Drives regulatory and tax compliance rules.",
        "valid_values": ["US", "CA", "GB", "DE", "AU", "IN", "JP", "BR"],
        "sample_values": ["US", "CA", "GB"],
        "formula": None,
        "business_rules": [
            "Determines which regulatory framework applies (e.g., ACA for US, NHS interplay for GB)",
            "Affects currency defaults and tax treatment of benefits",
            "Multi-country clients have one record per country or a single HQ record",
        ],
        "lineage": {"source_system": "CRM / Onboarding", "load_frequency": "At onboarding", "transformation": "Standardized to ISO 3166-1 alpha-2"},
        "used_in_metrics": ["Client distribution by country", "Regulatory compliance scope"],
        "relationships": ["May differ from regions.country_code (regions are more granular)"],
    },
    "clients.contract_start_date": {
        "business_name": "Contract Start Date",
        "business_description": "The date the client's service agreement with the HCM platform became effective. Used for billing, SLA tracking, and client tenure calculations.",
        "valid_values": None,
        "sample_values": ["2020-01-01", "2023-07-15", "2025-04-01"],
        "formula": None,
        "business_rules": [
            "Immutable once set — represents original contract execution date",
            "Client tenure = DATEDIFF(year, contract_start_date, CURRENT_DATE)",
            "Used with is_active to determine contract lifecycle stage",
            "Renewals do not change contract_start_date (tracked separately)",
        ],
        "lineage": {"source_system": "Contract Management / CRM", "load_frequency": "At onboarding", "transformation": "Direct copy from executed contract"},
        "used_in_metrics": ["Client tenure distribution", "Revenue cohort analysis", "Contract renewal pipeline"],
        "relationships": ["Used with is_active to derive contract status"],
    },
    # ── regions (all) ──
    "regions.region_id": {
        "business_name": "Region Identifier",
        "business_description": "Unique identifier for a geographic region within a client's organizational structure.",
        "valid_values": None,
        "sample_values": ["REG-US-EAST", "REG-US-WEST", "REG-CA-ON"],
        "formula": None,
        "business_rules": [
            "Scoped to a single client (client_id + region_id is unique)",
            "Regions may map to states, provinces, or custom geographic groupings",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At setup", "transformation": "Generated at client configuration"},
        "used_in_metrics": ["Regional enrollment breakdown", "Geographic compliance tracking"],
        "relationships": ["Referenced by: employees.region_id, plan_eligibility_rules.region_id"],
    },
    "regions.client_id": {
        "business_name": "Client Reference",
        "business_description": "Foreign key linking this region to the owning client company. Ensures multi-tenant data isolation.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002"],
        "formula": None,
        "business_rules": [
            "Every region belongs to exactly one client",
            "Must match a valid client_id in the clients table",
            "Queries should always filter by client_id for tenant isolation",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At setup", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → clients.client_id"],
    },
    "regions.region_name": {
        "business_name": "Region Display Name",
        "business_description": "Human-readable name for the region, shown in reports and UI. Can be a state name, office location, or custom label.",
        "valid_values": None,
        "sample_values": ["Northeast", "West Coast", "Ontario", "London Office"],
        "formula": None,
        "business_rules": [
            "Unique within a client (no two regions with the same name for one company)",
            "Used as grouping label in enrollment and cost reports",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At setup", "transformation": "Direct from client configuration"},
        "used_in_metrics": ["Enrollment by region", "Regional cost comparison"],
        "relationships": [],
    },
    "regions.country_code": {
        "business_name": "Region Country Code",
        "business_description": "ISO country code for this specific region. Important for multi-country clients where different regions operate under different regulatory regimes.",
        "valid_values": ["US", "CA", "GB", "DE", "AU"],
        "sample_values": ["US", "CA"],
        "formula": None,
        "business_rules": [
            "Must be a valid ISO 3166-1 alpha-2 code",
            "Drives which regulatory rules apply to employees in this region",
            "For single-country clients, will match clients.country_code",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At setup", "transformation": "Standardized to ISO alpha-2"},
        "used_in_metrics": ["Multi-country regulatory compliance", "Benefits by country"],
        "relationships": ["Related to: clients.country_code"],
    },
    "regions.state_province": {
        "business_name": "State or Province",
        "business_description": "Sub-national administrative division. Critical for US state-level mandates (e.g., state-mandated disability, paid family leave).",
        "valid_values": None,
        "sample_values": ["CA", "NY", "TX", "ON", "BC"],
        "formula": None,
        "business_rules": [
            "Uses standard postal abbreviations (US: 2-letter state code; CA: 2-letter province code)",
            "Drives state-specific mandated benefits (e.g., NY Paid Family Leave, CA SDI)",
            "Nullable for non-US/CA regions or when not applicable",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At setup", "transformation": "Standardized to postal abbreviation"},
        "used_in_metrics": ["State-level mandate compliance", "State enrollment distribution"],
        "relationships": [],
    },
    "regions.regulatory_zone": {
        "business_name": "Regulatory Zone",
        "business_description": "Classification that determines which benefits regulations apply. Primarily used for ACA Applicable Large Employer (ALE) determination in the US.",
        "valid_values": ["ACA_applicable", "non_ACA", "provincial_mandate", "EU_directive"],
        "sample_values": ["ACA_applicable", "non_ACA"],
        "formula": None,
        "business_rules": [
            "'ACA_applicable' — US regions where ACA employer mandate applies (50+ FTE companies)",
            "'non_ACA' — US regions for small employers or non-US regions",
            "'provincial_mandate' — Canadian provinces with mandated benefits",
            "'EU_directive' — European regions under EU benefits directives",
            "Drives eligibility requirements and reporting obligations (e.g., ACA 1094-C/1095-C)",
        ],
        "lineage": {"source_system": "Compliance Engine", "load_frequency": "Annual review", "transformation": "Derived from company size, location, and regulatory database"},
        "used_in_metrics": ["ACA compliance tracking", "Regulatory zone coverage analysis"],
        "relationships": ["Affects: plan_eligibility_rules applicability"],
    },
    # ── salary_bands (all) ──
    "salary_bands.salary_band_id": {
        "business_name": "Salary Band Identifier",
        "business_description": "Unique identifier for a salary tier within a client's compensation structure.",
        "valid_values": None,
        "sample_values": ["SB-001", "SB-002", "SB-EXEC"],
        "formula": None,
        "business_rules": ["Scoped to a single client", "Referenced by employees and plan_eligibility_rules"],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "Annual review", "transformation": "Generated at compensation setup"},
        "used_in_metrics": [],
        "relationships": ["Referenced by: employees.salary_band_id, plan_eligibility_rules.salary_band_id"],
    },
    "salary_bands.client_id": {
        "business_name": "Client Reference",
        "business_description": "Foreign key linking this salary band to the owning client. Each client defines their own salary band structure.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002"],
        "formula": None,
        "business_rules": ["Salary bands are client-specific", "Must match a valid client_id"],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "At setup", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → clients.client_id"],
    },
    "salary_bands.band_name": {
        "business_name": "Salary Band Name",
        "business_description": "Human-readable label for the salary tier. Used to determine plan eligibility and employer contribution levels.",
        "valid_values": None,
        "sample_values": ["Band 1 (Entry)", "Band 2 (Mid)", "Band 3 (Senior)", "Executive"],
        "formula": None,
        "business_rules": [
            "Defined by client's compensation philosophy",
            "Typically 3-6 bands covering entry to executive levels",
            "Higher bands may have access to additional plans (e.g., executive life insurance)",
            "Band assignment affects employer contribution percentages",
        ],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "Annual", "transformation": "Direct from compensation structure"},
        "used_in_metrics": ["Enrollment by salary tier", "Benefits cost by compensation level"],
        "relationships": [],
    },
    "salary_bands.min_salary": {
        "business_name": "Minimum Salary",
        "business_description": "Lower bound of the salary range for this band. Used together with max_salary to classify employees into bands.",
        "valid_values": None,
        "sample_values": ["30000.00", "60000.00", "100000.00"],
        "formula": None,
        "business_rules": [
            "Inclusive lower bound: employee salary >= min_salary",
            "Bands should be contiguous (max of band N = min of band N+1)",
            "Currency specified by currency_code column",
            "Updated annually during compensation review cycle",
        ],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "Annual", "transformation": "Direct from comp structure"},
        "used_in_metrics": ["Salary distribution analysis", "ACA affordability threshold checks"],
        "relationships": ["Paired with: max_salary to define band range"],
    },
    "salary_bands.max_salary": {
        "business_name": "Maximum Salary",
        "business_description": "Upper bound of the salary range for this band.",
        "valid_values": None,
        "sample_values": ["59999.99", "99999.99", "250000.00"],
        "formula": None,
        "business_rules": [
            "Exclusive upper bound for non-top bands",
            "Top band may use a very high sentinel value (e.g., 999999.99) or NULL for uncapped",
            "Employee assignment: min_salary <= actual_salary < max_salary",
        ],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "Annual", "transformation": "Direct from comp structure"},
        "used_in_metrics": ["Salary band distribution"],
        "relationships": ["Paired with: min_salary"],
    },
    "salary_bands.currency_code": {
        "business_name": "Currency Code",
        "business_description": "ISO 4217 currency code for the salary amounts in this band.",
        "valid_values": ["USD", "CAD", "GBP", "EUR", "AUD"],
        "sample_values": ["USD", "CAD", "GBP"],
        "formula": None,
        "business_rules": [
            "All monetary values within the band use this currency",
            "Cross-currency comparisons require FX conversion",
            "Typically matches the country_code of the client or region",
        ],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "At setup", "transformation": "Standardized to ISO 4217"},
        "used_in_metrics": ["Currency-normalized cost analysis"],
        "relationships": ["Also used in: benefit_plan_options.currency_code"],
    },
    # ── benefit_plans (remaining) ──
    "benefit_plans.plan_id": {
        "business_name": "Plan Identifier",
        "business_description": "Unique identifier for a specific benefit plan offering. A new plan_id is created each plan year even for the same plan name.",
        "valid_values": None,
        "sample_values": ["PLN-MED-001-2026", "PLN-DEN-002-2026"],
        "formula": None,
        "business_rules": [
            "Unique across all clients and plan years",
            "Convention typically: PLN-{type}-{seq}-{year}",
            "Historical plan_ids are retained for year-over-year comparison",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual (plan year setup)", "transformation": "Generated during plan configuration"},
        "used_in_metrics": ["Plan-level enrollment counts", "Plan cost tracking"],
        "relationships": ["Referenced by: benefit_enrollments.plan_id, plan_eligibility_rules.plan_id, benefit_plan_options.plan_id"],
    },
    "benefit_plans.client_id": {
        "business_name": "Client Reference",
        "business_description": "Foreign key linking this plan to the owning client. Plans are client-specific — each company has its own plan catalog.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002"],
        "formula": None,
        "business_rules": ["Plans are tenant-scoped", "Cross-client plan comparison requires normalization by plan_type"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "At plan setup", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → clients.client_id"],
    },
    "benefit_plans.plan_name": {
        "business_name": "Plan Display Name",
        "business_description": "Human-readable name of the benefit plan as it appears to employees during enrollment. Includes carrier or tier info.",
        "valid_values": None,
        "sample_values": ["Blue Cross PPO Gold", "Delta Dental Basic", "VSP Vision Plus", "MetLife Basic Life 1x"],
        "formula": None,
        "business_rules": [
            "Must be unique within a client for a given plan_year",
            "Typically includes carrier name and tier/level for employee clarity",
            "Displayed on enrollment forms, benefits summaries, and ID cards",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct from plan configuration"},
        "used_in_metrics": ["Plan-level enrollment report labels", "Plan comparison dashboards"],
        "relationships": [],
    },
    "benefit_plans.carrier_name": {
        "business_name": "Insurance Carrier Name",
        "business_description": "The insurance company or administrator that underwrites or administers this plan.",
        "valid_values": None,
        "sample_values": ["Blue Cross Blue Shield", "Aetna", "UnitedHealthcare", "Delta Dental", "MetLife", "VSP"],
        "formula": None,
        "business_rules": [
            "Carrier may change year-to-year if client switches providers",
            "Self-insured plans list the TPA (Third Party Administrator) here",
            "Used for carrier performance reporting and contract negotiations",
        ],
        "lineage": {"source_system": "Benefits Admin / Carrier contracts", "load_frequency": "Annual", "transformation": "Standardized carrier name from contract records"},
        "used_in_metrics": ["Claims by carrier", "Carrier performance scoring", "Network adequacy"],
        "relationships": [],
    },
    "benefit_plans.is_active": {
        "business_name": "Active Plan Flag",
        "business_description": "Indicates whether this plan is currently offered for enrollment. Historical plans are marked inactive but retained.",
        "valid_values": ["TRUE", "FALSE"],
        "sample_values": ["TRUE", "FALSE"],
        "formula": "TRUE when plan_year = current plan year AND client has not terminated the plan",
        "business_rules": [
            "Only active plans appear in enrollment options",
            "Set to FALSE at the end of a plan year when replaced by next year's plan",
            "Also set to FALSE if plan is discontinued mid-year (rare)",
            "Queries for current offerings should filter: is_active = TRUE",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual + event-driven", "transformation": "Derived from plan year lifecycle"},
        "used_in_metrics": ["Active plan count by type", "Plan discontinuation tracking"],
        "relationships": [],
    },
    "benefit_plans.created_at": {
        "business_name": "Plan Created Timestamp",
        "business_description": "System timestamp when this plan record was created. Used for audit trail and data lineage.",
        "valid_values": None,
        "sample_values": ["2025-09-15T14:30:00Z", "2025-10-01T09:00:00Z"],
        "formula": None,
        "business_rules": ["Auto-generated at record creation", "Immutable", "Stored in UTC"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "At plan creation", "transformation": "System-generated timestamp"},
        "used_in_metrics": ["Plan setup audit trail"],
        "relationships": [],
    },
    # ── plan_eligibility_rules (remaining) ──
    "plan_eligibility_rules.rule_id": {
        "business_name": "Eligibility Rule Identifier",
        "business_description": "Unique identifier for a specific eligibility rule. Each rule defines conditions under which employees can enroll in a plan.",
        "valid_values": None,
        "sample_values": ["RULE-001", "RULE-002"],
        "formula": None,
        "business_rules": ["Auto-generated", "A plan may have multiple rules for different employee segments"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Generated at rule creation"},
        "used_in_metrics": [],
        "relationships": ["Parent of this rule set: benefit_plans.plan_id"],
    },
    "plan_eligibility_rules.plan_id": {
        "business_name": "Plan Reference",
        "business_description": "Foreign key to the benefit plan this eligibility rule applies to.",
        "valid_values": None,
        "sample_values": ["PLN-MED-001-2026"],
        "formula": None,
        "business_rules": ["Each rule belongs to exactly one plan", "A plan may have 1-N rules"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → benefit_plans.plan_id"],
    },
    "plan_eligibility_rules.region_id": {
        "business_name": "Region Restriction",
        "business_description": "If set, this rule only applies to employees in the specified region. NULL means the rule applies to all regions.",
        "valid_values": None,
        "sample_values": ["REG-US-EAST", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = rule applies regardless of employee region",
            "When set, only employees with matching region_id are governed by this rule",
            "Allows different eligibility criteria by geography (e.g., different waiting periods by state)",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "FK reference or NULL"},
        "used_in_metrics": ["Regional eligibility rule coverage"],
        "relationships": ["FK → regions.region_id"],
    },
    "plan_eligibility_rules.salary_band_id": {
        "business_name": "Salary Band Restriction",
        "business_description": "If set, this rule only applies to employees in the specified salary band. NULL means no salary-based restriction.",
        "valid_values": None,
        "sample_values": ["SB-EXEC", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = rule applies regardless of salary band",
            "Used for executive-only plans or tiered employer contribution rules",
            "Example: Executive Life Insurance only available to SB-EXEC band",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "FK reference or NULL"},
        "used_in_metrics": ["Salary-tier plan access analysis"],
        "relationships": ["FK → salary_bands.salary_band_id"],
    },
    "plan_eligibility_rules.employment_type": {
        "business_name": "Employment Type Restriction",
        "business_description": "If set, restricts this eligibility rule to employees of a specific employment type. NULL means all types.",
        "valid_values": ["full_time", "part_time", "contractor", None],
        "sample_values": ["full_time", "part_time", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = rule applies regardless of employment type",
            "Most plans restrict to full_time; some include part_time",
            "Contractors are almost never eligible for employer-sponsored benefits",
            "Combined with region and salary band for granular eligibility targeting",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct from plan configuration"},
        "used_in_metrics": ["Part-time benefits eligibility gap analysis"],
        "relationships": ["Cross-referenced with: employees.employment_type"],
    },
    # ── benefit_plan_options (remaining) ──
    "benefit_plan_options.option_id": {
        "business_name": "Plan Option Identifier",
        "business_description": "Unique identifier for a specific coverage tier within a plan (e.g., Employee Only PPO Gold).",
        "valid_values": None,
        "sample_values": ["OPT-001", "OPT-002"],
        "formula": None,
        "business_rules": ["One plan has multiple options (one per coverage level)", "Typically 4 options per plan: EE, EE+SP, EE+CH, FAM"],
        "lineage": {"source_system": "Benefits Admin / Carrier", "load_frequency": "Annual", "transformation": "Generated at plan option setup"},
        "used_in_metrics": [],
        "relationships": ["Referenced by: benefit_enrollments.option_id"],
    },
    "benefit_plan_options.plan_id": {
        "business_name": "Plan Reference",
        "business_description": "Foreign key to the parent benefit plan this option belongs to.",
        "valid_values": None,
        "sample_values": ["PLN-MED-001-2026"],
        "formula": None,
        "business_rules": ["Each option belongs to one plan", "Options inherit plan_type from parent plan"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → benefit_plans.plan_id"],
    },
    "benefit_plan_options.deductible_amount": {
        "business_name": "Annual Deductible",
        "business_description": "The amount the employee must pay out-of-pocket before the plan begins paying. Resets each plan year.",
        "valid_values": None,
        "sample_values": ["500.00", "1500.00", "3000.00", "6000.00"],
        "formula": None,
        "business_rules": [
            "Applies per plan year (resets Jan 1 for calendar-year plans)",
            "HDHP plans have higher deductibles ($1,650+ individual / $3,300+ family for 2026)",
            "Preventive care is exempt from deductible (ACA mandate)",
            "Family deductible is typically 2x individual deductible",
            "Claims reduce deductible remaining: deductible_remaining = deductible_amount - SUM(employee_responsibility for deductible claims)",
        ],
        "lineage": {"source_system": "Carrier rate tables", "load_frequency": "Annual", "transformation": "Direct from plan design documents"},
        "used_in_metrics": ["Deductible met percentage", "Average deductible by plan type", "HDHP vs PPO cost comparison"],
        "relationships": ["Tracked against: benefit_claims.employee_responsibility accumulator"],
    },
    "benefit_plan_options.oop_max": {
        "business_name": "Out-of-Pocket Maximum",
        "business_description": "The maximum amount an employee will pay in a plan year for covered services. After reaching oop_max, the plan covers 100%.",
        "valid_values": None,
        "sample_values": ["4000.00", "7500.00", "9200.00"],
        "formula": None,
        "business_rules": [
            "ACA maximum for 2026: $9,450 individual / $18,900 family",
            "Includes deductible, copays, and coinsurance",
            "Does NOT include premiums or out-of-network balance billing",
            "Once reached, plan pays 100% of allowed amount for the rest of the year",
            "OOP accumulator: SUM(employee_responsibility) toward oop_max",
        ],
        "lineage": {"source_system": "Carrier rate tables", "load_frequency": "Annual", "transformation": "Direct from plan design"},
        "used_in_metrics": ["OOP max utilization rate", "Catastrophic cost exposure analysis"],
        "relationships": ["Caps: benefit_claims.employee_responsibility for the plan year"],
    },
    "benefit_plan_options.currency_code": {
        "business_name": "Currency Code",
        "business_description": "ISO 4217 currency for all monetary values in this plan option (costs, deductible, OOP max).",
        "valid_values": ["USD", "CAD", "GBP", "EUR"],
        "sample_values": ["USD"],
        "formula": None,
        "business_rules": ["All monetary fields in this row use this currency", "Typically matches the client's primary country"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Standardized to ISO 4217"},
        "used_in_metrics": [],
        "relationships": ["Related to: salary_bands.currency_code"],
    },
    # ── employees (remaining) ──
    "employees.client_id": {
        "business_name": "Client Reference",
        "business_description": "Foreign key to the employing client company. Critical for multi-tenant isolation — all employee queries must filter by client_id.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002"],
        "formula": None,
        "business_rules": ["Every employee belongs to exactly one client", "Must be included in all queries for tenant isolation"],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At hire", "transformation": "FK reference"},
        "used_in_metrics": ["Per-client headcount", "Client-level benefits utilization"],
        "relationships": ["FK → clients.client_id"],
    },
    "employees.employee_number": {
        "business_name": "Employee Number (PII)",
        "business_description": "Human-readable employee identifier used in HR systems and on pay stubs. Classified as PII — do not expose in reports.",
        "valid_values": None,
        "sample_values": ["EMP-12345", "100234", "A-98765"],
        "formula": None,
        "business_rules": [
            "⚠️ PII: Must be masked or excluded from analytics outputs",
            "Format varies by client (numeric, alphanumeric, prefixed)",
            "May be reused across rehires (unlike employee_id which is unique per record)",
            "Used for HR system lookups, not for analytical joins",
        ],
        "lineage": {"source_system": "HCM Core / HRIS", "load_frequency": "At hire", "transformation": "Direct copy, PII-flagged"},
        "used_in_metrics": ["Never used directly in metrics — use employee_id instead"],
        "relationships": ["PII — see employee_id for join key"],
    },
    "employees.region_id": {
        "business_name": "Employee Region",
        "business_description": "Foreign key to the region where the employee is based. Determines which eligibility rules and regulatory requirements apply.",
        "valid_values": None,
        "sample_values": ["REG-US-EAST", "REG-CA-ON"],
        "formula": None,
        "business_rules": [
            "Determines applicable regulatory zone (ACA, state mandates)",
            "Used by plan_eligibility_rules to filter region-specific plans",
            "May change if employee transfers offices",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "FK reference from employee work location"},
        "used_in_metrics": ["Regional headcount", "Enrollment by region"],
        "relationships": ["FK → regions.region_id", "Cross-ref: plan_eligibility_rules.region_id"],
    },
    "employees.department_id": {
        "business_name": "Employee Department",
        "business_description": "Foreign key to the employee's organizational department. Used for cost allocation and departmental reporting.",
        "valid_values": None,
        "sample_values": ["DEPT-ENG", "DEPT-SALES", "DEPT-HR"],
        "formula": None,
        "business_rules": [
            "Employee belongs to one department at a time",
            "Department changes tracked via HR transactions",
            "Used for benefits cost allocation to department cost centers",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": ["Enrollment rate by department", "Benefits cost by department"],
        "relationships": ["FK → departments.department_id"],
    },
    "employees.salary_band_id": {
        "business_name": "Employee Salary Band",
        "business_description": "Foreign key to the salary band the employee falls into. Drives plan eligibility and employer contribution levels.",
        "valid_values": None,
        "sample_values": ["SB-001", "SB-002", "SB-EXEC"],
        "formula": "Assigned by matching actual salary to salary_bands.min_salary / max_salary range",
        "business_rules": [
            "Updated when employee salary changes (promotion, annual increase)",
            "Affects which plans the employee can enroll in (via plan_eligibility_rules)",
            "Executive bands may unlock supplemental benefits",
        ],
        "lineage": {"source_system": "Compensation Module", "load_frequency": "At salary change", "transformation": "Derived from salary-to-band mapping"},
        "used_in_metrics": ["Benefits by compensation tier", "Executive benefits utilization"],
        "relationships": ["FK → salary_bands.salary_band_id"],
    },
    "employees.job_title": {
        "business_name": "Job Title",
        "business_description": "The employee's current job title. Descriptive field used in reporting; not typically used for eligibility logic.",
        "valid_values": None,
        "sample_values": ["Software Engineer", "Benefits Analyst", "VP of Sales", "Warehouse Associate"],
        "formula": None,
        "business_rules": [
            "Free-text field — not standardized across clients",
            "Not used for eligibility decisions (use employment_type and salary_band instead)",
            "May be useful for demographic analysis of benefits uptake",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "Direct copy"},
        "used_in_metrics": ["Benefits enrollment by job family (if job titles are categorized)"],
        "relationships": [],
    },
    "employees.termination_date": {
        "business_name": "Termination Date",
        "business_description": "The date the employee's employment ended. NULL for currently active or on-leave employees.",
        "valid_values": None,
        "sample_values": ["2025-12-31", "2026-02-15", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = employee is currently active or on leave",
            "Populated when employment_status changes to 'terminated'",
            "Benefits coverage typically ends on termination_date (or end of month, per client policy)",
            "COBRA continuation rights begin after termination_date (US only)",
            "Tenure at termination: DATEDIFF(day, hire_date, termination_date)",
        ],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time event-driven", "transformation": "Direct from HR termination transaction"},
        "used_in_metrics": ["Attrition rate", "COBRA eligibility tracking", "Average tenure at exit"],
        "relationships": ["Triggers: benefit_enrollments.enrollment_status → 'terminated'"],
    },
    # ── departments (remaining) ──
    "departments.department_id": {
        "business_name": "Department Identifier",
        "business_description": "Unique identifier for an organizational department within a client company.",
        "valid_values": None,
        "sample_values": ["DEPT-ENG", "DEPT-HR", "DEPT-SALES"],
        "formula": None,
        "business_rules": ["Scoped to a client (client_id + department_id is unique)", "Used as grouping dimension in departmental reports"],
        "lineage": {"source_system": "HCM Core / Org Chart", "load_frequency": "Real-time", "transformation": "From org structure"},
        "used_in_metrics": ["Department-level enrollment", "Benefits cost allocation"],
        "relationships": ["Referenced by: employees.department_id", "Self-ref: parent_department_id for hierarchy"],
    },
    "departments.client_id": {
        "business_name": "Client Reference",
        "business_description": "Foreign key to the client company. Departments are client-specific.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002"],
        "formula": None,
        "business_rules": ["Every department belongs to one client", "Used for tenant isolation"],
        "lineage": {"source_system": "HCM Core", "load_frequency": "At setup", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → clients.client_id"],
    },
    "departments.department_name": {
        "business_name": "Department Name",
        "business_description": "Human-readable department name used in reports and organizational charts.",
        "valid_values": None,
        "sample_values": ["Engineering", "Human Resources", "Sales & Marketing", "Finance"],
        "formula": None,
        "business_rules": [
            "Unique within a client organization",
            "Used as grouping label in enrollment and cost reports",
            "May include sub-department names for leaf nodes (e.g., 'Engineering — Backend')",
        ],
        "lineage": {"source_system": "HCM Core / Org Chart", "load_frequency": "Real-time", "transformation": "Direct copy"},
        "used_in_metrics": ["Enrollment rate by department", "Benefits cost per department"],
        "relationships": [],
    },
    # ── benefit_enrollments (remaining) ──
    "benefit_enrollments.enrollment_id": {
        "business_name": "Enrollment Identifier",
        "business_description": "Unique identifier for a specific enrollment record — one employee enrolling in one plan for one coverage period.",
        "valid_values": None,
        "sample_values": ["ENR-100001", "ENR-100002"],
        "formula": None,
        "business_rules": [
            "New enrollment_id created for each enrollment action (new, change, re-enroll)",
            "Historical enrollments retained for audit and trend analysis",
            "Grain: one record per employee per plan per enrollment period",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "Generated at enrollment creation"},
        "used_in_metrics": ["Enrollment count (distinct enrollments vs distinct employees)"],
        "relationships": ["Referenced by: dependent_enrollments.enrollment_id, benefit_claims.enrollment_id"],
    },
    "benefit_enrollments.employee_id": {
        "business_name": "Employee Reference",
        "business_description": "Foreign key to the employee who is enrolled in this plan.",
        "valid_values": None,
        "sample_values": ["EMP-10001", "EMP-10002"],
        "formula": None,
        "business_rules": [
            "An employee can have multiple enrollments (one per plan type, plus historical)",
            "Active enrollment constraint: at most ONE active enrollment per employee per plan_type",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": ["Enrollment rate uses COUNT(DISTINCT employee_id)"],
        "relationships": ["FK → employees.employee_id"],
    },
    "benefit_enrollments.plan_id": {
        "business_name": "Plan Reference",
        "business_description": "Foreign key to the benefit plan the employee is enrolled in.",
        "valid_values": None,
        "sample_values": ["PLN-MED-001-2026"],
        "formula": None,
        "business_rules": ["Links enrollment to specific plan and plan year", "Used to derive plan_type for reporting"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": ["Enrollment by plan"],
        "relationships": ["FK → benefit_plans.plan_id"],
    },
    "benefit_enrollments.option_id": {
        "business_name": "Plan Option Reference",
        "business_description": "Foreign key to the specific coverage tier (e.g., Employee Only, Family) selected by the employee.",
        "valid_values": None,
        "sample_values": ["OPT-001", "OPT-004"],
        "formula": None,
        "business_rules": [
            "Determines the cost (employee + employer premium) for this enrollment",
            "Must match an option that belongs to the referenced plan_id",
            "Coverage level must be consistent with dependents on the enrollment",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": ["Coverage tier distribution"],
        "relationships": ["FK → benefit_plan_options.option_id"],
    },
    "benefit_enrollments.termination_date": {
        "business_name": "Enrollment End Date",
        "business_description": "The date coverage under this enrollment ends. NULL for currently active enrollments.",
        "valid_values": None,
        "sample_values": ["2025-12-31", "2026-06-30", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = enrollment is currently active",
            "Set when: employee terminates, changes plans, or enrollment is canceled",
            "Active enrollment window: effective_date <= reference_date AND (termination_date IS NULL OR reference_date < termination_date)",
            "For OE plan changes: old enrollment gets termination_date = Dec 31, new one starts Jan 1",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time event-driven", "transformation": "Set by enrollment lifecycle events"},
        "used_in_metrics": ["Point-in-time enrollment snapshots", "Coverage duration analysis"],
        "relationships": ["Paired with: effective_date to define active window"],
    },
    "benefit_enrollments.created_at": {
        "business_name": "Enrollment Created Timestamp",
        "business_description": "System timestamp when the enrollment record was created. Used for audit trail.",
        "valid_values": None,
        "sample_values": ["2025-11-15T10:30:00Z", "2026-01-02T08:00:00Z"],
        "formula": None,
        "business_rules": ["Auto-generated, immutable", "Stored in UTC", "Used for OE completion timeline tracking"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "At enrollment creation", "transformation": "System-generated"},
        "used_in_metrics": ["OE enrollment completion rate by day"],
        "relationships": [],
    },
    # ── dependents (remaining) ──
    "dependents.dependent_id": {
        "business_name": "Dependent Identifier",
        "business_description": "Unique identifier for a dependent individual linked to an employee.",
        "valid_values": None,
        "sample_values": ["DEP-50001", "DEP-50002"],
        "formula": None,
        "business_rules": ["One record per dependent person", "A dependent belongs to exactly one employee"],
        "lineage": {"source_system": "HCM Core / Benefits Admin", "load_frequency": "Real-time", "transformation": "Generated at dependent registration"},
        "used_in_metrics": ["Average dependents per employee"],
        "relationships": ["Referenced by: dependent_enrollments.dependent_id"],
    },
    "dependents.employee_id": {
        "business_name": "Employee Reference",
        "business_description": "Foreign key to the employee who listed this dependent.",
        "valid_values": None,
        "sample_values": ["EMP-10001", "EMP-10002"],
        "formula": None,
        "business_rules": ["Each dependent belongs to one employee", "Employee's coverage level must match dependents (e.g., cannot have 'employee_only' coverage with dependents)"],
        "lineage": {"source_system": "HCM Core", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": ["Employees with dependents count"],
        "relationships": ["FK → employees.employee_id"],
    },
    "dependents.date_of_birth": {
        "business_name": "Dependent Date of Birth (PII)",
        "business_description": "The dependent's date of birth. Classified as PII. Used to determine age-based eligibility (child age-out at 26).",
        "valid_values": None,
        "sample_values": ["2005-06-15", "1990-03-22"],
        "formula": None,
        "business_rules": [
            "⚠️ PII: Must be masked or excluded from analytics outputs",
            "Child dependents age out of medical coverage at age 26 (ACA)",
            "Age calculated: DATEDIFF(year, date_of_birth, CURRENT_DATE)",
            "Dental/vision child age limits vary by carrier (often 19 or 26)",
        ],
        "lineage": {"source_system": "HCM Core / Benefits Admin", "load_frequency": "At dependent registration", "transformation": "Direct copy, PII-flagged"},
        "used_in_metrics": ["Age-out forecasting (children approaching 26)", "Dependent age distribution"],
        "relationships": ["Used for: child age-out eligibility checks"],
    },
    "dependents.is_active": {
        "business_name": "Active Dependent Flag",
        "business_description": "Indicates whether the dependent is currently active and eligible for coverage.",
        "valid_values": ["TRUE", "FALSE"],
        "sample_values": ["TRUE", "FALSE"],
        "formula": "FALSE when: relationship = 'child' AND age >= 26, OR dependent removed by employee, OR divorce (spouse)",
        "business_rules": [
            "Inactive dependents cannot be added to new enrollments",
            "Existing enrollments for inactive dependents should be terminated",
            "Child dependents auto-inactivated at age 26 (configurable by carrier)",
            "Spouse set to inactive upon divorce notification",
        ],
        "lineage": {"source_system": "Benefits Admin / Eligibility Engine", "load_frequency": "Nightly batch + event-driven", "transformation": "Derived from age rules and HR events"},
        "used_in_metrics": ["Active dependent count", "Dependent churn rate"],
        "relationships": ["Affects: dependent_enrollments eligibility"],
    },
    # ── dependent_enrollments (all) ──
    "dependent_enrollments.dependent_enrollment_id": {
        "business_name": "Dependent Enrollment Identifier",
        "business_description": "Unique identifier for a specific dependent's coverage under an employee's enrollment.",
        "valid_values": None,
        "sample_values": ["DENR-70001", "DENR-70002"],
        "formula": None,
        "business_rules": ["Grain: one record per dependent per employee enrollment", "Linked to the parent enrollment record"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "Generated at dependent enrollment"},
        "used_in_metrics": ["Dependent enrollment count"],
        "relationships": ["Child of: benefit_enrollments.enrollment_id"],
    },
    "dependent_enrollments.enrollment_id": {
        "business_name": "Parent Enrollment Reference",
        "business_description": "Foreign key to the employee's enrollment record that this dependent is covered under.",
        "valid_values": None,
        "sample_values": ["ENR-100001"],
        "formula": None,
        "business_rules": [
            "Dependent coverage is always tied to an employee enrollment",
            "If parent enrollment is terminated, all dependent enrollments under it are also terminated",
            "Coverage level of parent enrollment must include dependent coverage (not employee_only)",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → benefit_enrollments.enrollment_id"],
    },
    "dependent_enrollments.dependent_id": {
        "business_name": "Dependent Reference",
        "business_description": "Foreign key to the dependent individual covered under this enrollment.",
        "valid_values": None,
        "sample_values": ["DEP-50001"],
        "formula": None,
        "business_rules": ["Dependent must be active (is_active = TRUE) to be enrolled", "Must belong to the same employee as the parent enrollment"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → dependents.dependent_id"],
    },
    "dependent_enrollments.effective_date": {
        "business_name": "Dependent Coverage Start Date",
        "business_description": "The date the dependent's coverage under this enrollment begins.",
        "valid_values": None,
        "sample_values": ["2026-01-01", "2026-03-15"],
        "formula": None,
        "business_rules": [
            "Typically matches the parent enrollment's effective_date",
            "For mid-year additions (e.g., new baby): may be the birth/adoption date",
            "Must be >= parent enrollment's effective_date",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Real-time", "transformation": "Direct or derived from qualifying event date"},
        "used_in_metrics": ["Dependent addition volume by month"],
        "relationships": ["Must align with: benefit_enrollments.effective_date"],
    },
    "dependent_enrollments.termination_date": {
        "business_name": "Dependent Coverage End Date",
        "business_description": "The date the dependent's coverage ends. NULL if currently covered.",
        "valid_values": None,
        "sample_values": ["2026-12-31", "NULL"],
        "formula": None,
        "business_rules": [
            "NULL = dependent is currently covered",
            "Set when: dependent ages out, parent enrollment terminates, or dependent removed",
            "Cannot be later than parent enrollment's termination_date",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Event-driven", "transformation": "Set by lifecycle events"},
        "used_in_metrics": ["Dependent coverage duration"],
        "relationships": ["Constrained by: benefit_enrollments.termination_date"],
    },
    # ── benefit_claims (remaining) ──
    "benefit_claims.claim_id": {
        "business_name": "Claim Identifier",
        "business_description": "Unique identifier for a single claim submitted by a provider for services rendered to a covered member.",
        "valid_values": None,
        "sample_values": ["CLM-200001", "CLM-200002"],
        "formula": None,
        "business_rules": ["One claim per provider encounter/service", "Multiple claims may exist per member per day (different providers/services)"],
        "lineage": {"source_system": "Claims Processing / Carrier EDI 837", "load_frequency": "Daily batch", "transformation": "From carrier claim feed, deduplicated"},
        "used_in_metrics": ["Claim volume", "Claims per member per month (PMPM)"],
        "relationships": ["No child tables — leaf entity"],
    },
    "benefit_claims.enrollment_id": {
        "business_name": "Enrollment Reference",
        "business_description": "Foreign key to the enrollment under which this claim was processed. Links claims to the employee, plan, and coverage details.",
        "valid_values": None,
        "sample_values": ["ENR-100001"],
        "formula": None,
        "business_rules": [
            "Claim must belong to an enrollment that was active on the claim_date",
            "Used to join claims to: employee (via enrollment), plan, coverage level, and costs",
        ],
        "lineage": {"source_system": "Claims Processing", "load_frequency": "Daily batch", "transformation": "Matched to enrollment by carrier member ID"},
        "used_in_metrics": ["Claims cost per enrollment", "Loss ratio by plan"],
        "relationships": ["FK → benefit_enrollments.enrollment_id"],
    },
    "benefit_claims.claim_date": {
        "business_name": "Date of Service",
        "business_description": "The date the healthcare service was rendered. Used for plan year assignment and deductible/OOP accumulation.",
        "valid_values": None,
        "sample_values": ["2026-01-15", "2026-03-22"],
        "formula": None,
        "business_rules": [
            "Must fall within the enrollment's active coverage window",
            "Determines which plan year's deductible/OOP accumulator applies",
            "Claims may be submitted weeks/months after service date",
            "Lag between claim_date and processed_date is the 'claims processing lag'",
        ],
        "lineage": {"source_system": "Carrier EDI 837", "load_frequency": "Daily batch", "transformation": "From claim service date field"},
        "used_in_metrics": ["Monthly claims trend", "Seasonality analysis", "Claims IBNR (Incurred But Not Reported)"],
        "relationships": ["Must be within: benefit_enrollments.effective_date to termination_date"],
    },
    "benefit_claims.processed_date": {
        "business_name": "Claim Processed Date",
        "business_description": "The date the claim was adjudicated (payment/denial decided) by the insurance carrier.",
        "valid_values": None,
        "sample_values": ["2026-02-01", "2026-04-10"],
        "formula": None,
        "business_rules": [
            "NULL for claims in 'submitted' status (not yet adjudicated)",
            "Processing lag = processed_date - claim_date (typically 14-30 days)",
            "Used to determine which reporting period the payment falls into (paid date basis vs incurred date basis)",
            "Carrier SLA: must process 95% of claims within 30 days",
        ],
        "lineage": {"source_system": "Claims Processing / Carrier", "load_frequency": "Daily batch", "transformation": "From carrier adjudication record"},
        "used_in_metrics": ["Claims processing turnaround time", "IBNR estimation", "Paid claims by month"],
        "relationships": ["Follows: claim_date (always >= claim_date)"],
    },
    # ── open_enrollment_events (remaining) ──
    "open_enrollment_events.event_id": {
        "business_name": "OE Event Identifier",
        "business_description": "Unique identifier for an open enrollment event/window for a client.",
        "valid_values": None,
        "sample_values": ["OE-CLI001-2026", "OE-CLI002-2026"],
        "formula": None,
        "business_rules": ["Typically one per client per plan year", "Special OE events may occur for mid-year plan changes"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Generated at OE calendar setup"},
        "used_in_metrics": ["OE event count"],
        "relationships": [],
    },
    "open_enrollment_events.client_id": {
        "business_name": "Client Reference",
        "business_description": "Foreign key to the client company running this open enrollment event.",
        "valid_values": None,
        "sample_values": ["CLI-001", "CLI-002"],
        "formula": None,
        "business_rules": ["Each OE event belongs to one client", "Client may have one OE per plan year"],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "FK reference"},
        "used_in_metrics": [],
        "relationships": ["FK → clients.client_id"],
    },
    "open_enrollment_events.plan_year": {
        "business_name": "Plan Year",
        "business_description": "The plan year that elections made during this OE event will apply to.",
        "valid_values": None,
        "sample_values": ["2025", "2026", "2027"],
        "formula": None,
        "business_rules": [
            "OE window typically opens in fall for the following plan year (e.g., Nov 2025 OE → 2026 plan year)",
            "Elections take effect on the first day of the plan year (usually Jan 1)",
            "Related to: benefit_plans.plan_year for matching plans to OE events",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct from OE calendar"},
        "used_in_metrics": ["OE participation rate by plan year", "Year-over-year plan migration"],
        "relationships": ["Related to: benefit_plans.plan_year"],
    },
    "open_enrollment_events.open_enrollment_end": {
        "business_name": "Open Enrollment Window End",
        "business_description": "The last date employees can make or change benefit elections for the upcoming plan year.",
        "valid_values": None,
        "sample_values": ["2025-11-30", "2025-11-15"],
        "formula": None,
        "business_rules": [
            "Typical window duration: 2-4 weeks",
            "After this date, elections are locked until next OE or qualifying event",
            "Employees who miss the window are passively enrolled in their current plan",
            "HR may grant individual extensions in exceptional circumstances",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Annual", "transformation": "Direct from OE calendar configuration"},
        "used_in_metrics": ["OE window utilization (% who enroll by day)", "Last-day enrollment spike analysis"],
        "relationships": ["Paired with: open_enrollment_start"],
    },
    "open_enrollment_events.is_active": {
        "business_name": "Active OE Event Flag",
        "business_description": "Indicates whether this open enrollment window is currently active (accepting elections).",
        "valid_values": ["TRUE", "FALSE"],
        "sample_values": ["TRUE", "FALSE"],
        "formula": "TRUE when CURRENT_DATE BETWEEN open_enrollment_start AND open_enrollment_end",
        "business_rules": [
            "Only one OE event per client should be active at a time",
            "Used to show/hide enrollment options in the employee self-service portal",
            "Auto-set to FALSE after the end date passes",
        ],
        "lineage": {"source_system": "Benefits Admin", "load_frequency": "Daily", "transformation": "Derived from date comparison"},
        "used_in_metrics": ["Currently active OE events"],
        "relationships": ["Derived from: open_enrollment_start and open_enrollment_end dates"],
    },
}


_MOCK_SCHEMA = {
    "schema_name": "HCM_ANALYTICS",
    "tables": [
        {
            "table_name": "clients",
            "description": "Companies/customers using the HCM platform",
            "columns": [
                {"name": "client_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_name", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Company name"},
                {"name": "industry", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Industry vertical"},
                {"name": "country_code", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Country code"},
                {"name": "is_active", "type": "BOOLEAN", "is_pk": False, "is_pii": False, "description": "Active client flag"},
                {"name": "contract_start_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Contract start"},
            ],
            "foreign_keys": [],
        },
        {
            "table_name": "regions",
            "description": "Geographic regions with regulatory context",
            "columns": [
                {"name": "region_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to clients"},
                {"name": "region_name", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Region display name"},
                {"name": "country_code", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Country"},
                {"name": "state_province", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "State or province"},
                {"name": "regulatory_zone", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "e.g. ACA_applicable, non_ACA"},
            ],
            "foreign_keys": [{"column": "client_id", "references": "clients.client_id"}],
        },
        {
            "table_name": "salary_bands",
            "description": "Salary tiers that drive plan eligibility",
            "columns": [
                {"name": "salary_band_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to clients"},
                {"name": "band_name", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "e.g. band_1, executive"},
                {"name": "min_salary", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Minimum salary"},
                {"name": "max_salary", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Maximum salary"},
                {"name": "currency_code", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Currency"},
            ],
            "foreign_keys": [{"column": "client_id", "references": "clients.client_id"}],
        },
        {
            "table_name": "benefit_plans",
            "description": "Master catalog of benefit plans (varies per client)",
            "columns": [
                {"name": "plan_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to clients"},
                {"name": "plan_name", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Plan display name"},
                {"name": "plan_type", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "medical/dental/vision/life/std/ltd/fsa/hsa"},
                {"name": "carrier_name", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Insurance carrier"},
                {"name": "plan_year", "type": "INT", "is_pk": False, "is_pii": False, "description": "Plan year"},
                {"name": "is_active", "type": "BOOLEAN", "is_pk": False, "is_pii": False, "description": "Active plan flag"},
                {"name": "created_at", "type": "TIMESTAMP", "is_pk": False, "is_pii": False, "description": "Created timestamp"},
            ],
            "foreign_keys": [{"column": "client_id", "references": "clients.client_id"}],
        },
        {
            "table_name": "plan_eligibility_rules",
            "description": "Which employees can enroll in which plans",
            "columns": [
                {"name": "rule_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "plan_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to benefit_plans"},
                {"name": "region_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to regions (nullable = all regions)"},
                {"name": "salary_band_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to salary_bands (nullable = all bands)"},
                {"name": "employment_type", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "full_time/part_time/contractor (nullable = all)"},
                {"name": "min_tenure_days", "type": "INT", "is_pk": False, "is_pii": False, "description": "Minimum days employed to be eligible"},
                {"name": "is_default", "type": "BOOLEAN", "is_pk": False, "is_pii": False, "description": "Default eligibility rule flag"},
            ],
            "foreign_keys": [
                {"column": "plan_id", "references": "benefit_plans.plan_id"},
                {"column": "region_id", "references": "regions.region_id"},
                {"column": "salary_band_id", "references": "salary_bands.salary_band_id"},
            ],
        },
        {
            "table_name": "benefit_plan_options",
            "description": "Coverage tiers and costs within a plan",
            "columns": [
                {"name": "option_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "plan_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to benefit_plans"},
                {"name": "coverage_level", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "employee_only/employee_spouse/employee_children/family"},
                {"name": "annual_employee_cost", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Annual cost to employee"},
                {"name": "annual_employer_cost", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Annual cost to employer"},
                {"name": "deductible_amount", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Annual deductible"},
                {"name": "oop_max", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Out-of-pocket maximum"},
                {"name": "currency_code", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Currency"},
            ],
            "foreign_keys": [{"column": "plan_id", "references": "benefit_plans.plan_id"}],
        },
        {
            "table_name": "employees",
            "description": "Core employee dimension",
            "columns": [
                {"name": "employee_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to clients"},
                {"name": "employee_number", "type": "VARCHAR", "is_pk": False, "is_pii": True, "description": "PII — employee identifier"},
                {"name": "region_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to regions"},
                {"name": "department_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to departments"},
                {"name": "salary_band_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to salary_bands"},
                {"name": "job_title", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Job title"},
                {"name": "employment_type", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "full_time/part_time/contractor"},
                {"name": "employment_status", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "active/terminated/leave"},
                {"name": "hire_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Hire date"},
                {"name": "termination_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Termination date"},
                {"name": "is_benefits_eligible", "type": "BOOLEAN", "is_pk": False, "is_pii": False, "description": "Benefits eligibility flag"},
            ],
            "foreign_keys": [
                {"column": "client_id", "references": "clients.client_id"},
                {"column": "region_id", "references": "regions.region_id"},
                {"column": "department_id", "references": "departments.department_id"},
                {"column": "salary_band_id", "references": "salary_bands.salary_band_id"},
            ],
        },
        {
            "table_name": "departments",
            "description": "Organizational hierarchy (per client)",
            "columns": [
                {"name": "department_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to clients"},
                {"name": "department_name", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Department name"},
                {"name": "parent_department_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Self-FK for hierarchy"},
                {"name": "cost_center_code", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "Cost center code"},
            ],
            "foreign_keys": [
                {"column": "client_id", "references": "clients.client_id"},
                {"column": "parent_department_id", "references": "departments.department_id"},
            ],
        },
        {
            "table_name": "benefit_enrollments",
            "description": "Actual enrollment records",
            "columns": [
                {"name": "enrollment_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "employee_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to employees"},
                {"name": "plan_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to benefit_plans"},
                {"name": "option_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to benefit_plan_options"},
                {"name": "enrollment_status", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "active/terminated/waived/pending"},
                {"name": "effective_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Enrollment effective date"},
                {"name": "termination_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Enrollment end date"},
                {"name": "enrollment_source", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "open_enrollment/new_hire/qualifying_event"},
                {"name": "created_at", "type": "TIMESTAMP", "is_pk": False, "is_pii": False, "description": "Created timestamp"},
            ],
            "foreign_keys": [
                {"column": "employee_id", "references": "employees.employee_id"},
                {"column": "plan_id", "references": "benefit_plans.plan_id"},
                {"column": "option_id", "references": "benefit_plan_options.option_id"},
            ],
        },
        {
            "table_name": "dependents",
            "description": "Employee dependents",
            "columns": [
                {"name": "dependent_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "employee_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to employees"},
                {"name": "relationship", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "spouse/child/domestic_partner"},
                {"name": "date_of_birth", "type": "DATE", "is_pk": False, "is_pii": True, "description": "PII — dependent DOB"},
                {"name": "is_active", "type": "BOOLEAN", "is_pk": False, "is_pii": False, "description": "Active dependent flag"},
            ],
            "foreign_keys": [{"column": "employee_id", "references": "employees.employee_id"}],
        },
        {
            "table_name": "dependent_enrollments",
            "description": "Which dependents are on which plans",
            "columns": [
                {"name": "dependent_enrollment_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "enrollment_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to benefit_enrollments"},
                {"name": "dependent_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to dependents"},
                {"name": "effective_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Coverage start"},
                {"name": "termination_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Coverage end"},
            ],
            "foreign_keys": [
                {"column": "enrollment_id", "references": "benefit_enrollments.enrollment_id"},
                {"column": "dependent_id", "references": "dependents.dependent_id"},
            ],
        },
        {
            "table_name": "benefit_claims",
            "description": "Claims submitted against plans",
            "columns": [
                {"name": "claim_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "enrollment_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to benefit_enrollments"},
                {"name": "claim_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Date of claim"},
                {"name": "claim_type", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "in_network/out_of_network/prescription/preventive"},
                {"name": "billed_amount", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Amount billed by provider"},
                {"name": "allowed_amount", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Amount allowed by plan"},
                {"name": "paid_amount", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Amount paid by plan"},
                {"name": "employee_responsibility", "type": "DECIMAL", "is_pk": False, "is_pii": False, "description": "Employee out-of-pocket"},
                {"name": "claim_status", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "submitted/processed/denied/appealed"},
                {"name": "processed_date", "type": "DATE", "is_pk": False, "is_pii": False, "description": "Date claim was processed"},
            ],
            "foreign_keys": [{"column": "enrollment_id", "references": "benefit_enrollments.enrollment_id"}],
        },
        {
            "table_name": "open_enrollment_events",
            "description": "Annual enrollment windows (per client)",
            "columns": [
                {"name": "event_id", "type": "VARCHAR", "is_pk": True, "is_pii": False, "description": "Primary key"},
                {"name": "client_id", "type": "VARCHAR", "is_pk": False, "is_pii": False, "description": "FK to clients"},
                {"name": "plan_year", "type": "INT", "is_pk": False, "is_pii": False, "description": "Plan year"},
                {"name": "open_enrollment_start", "type": "DATE", "is_pk": False, "is_pii": False, "description": "OE window start"},
                {"name": "open_enrollment_end", "type": "DATE", "is_pk": False, "is_pii": False, "description": "OE window end"},
                {"name": "is_active", "type": "BOOLEAN", "is_pk": False, "is_pii": False, "description": "Active OE flag"},
            ],
            "foreign_keys": [{"column": "client_id", "references": "clients.client_id"}],
        },
    ],
}

# ── Load persisted data (overrides hardcoded defaults with saved state) ──
_load_metadata()
_load_history()


# ── Application definitions: which tables/columns each app uses ──────
_APPLICATIONS = [
    {
        "app_id": "open-enrollment",
        "app_name": "Open Enrollment Management",
        "description": "Manages annual enrollment windows, employee plan elections, and coverage changes for the upcoming plan year.",
        "icon": "CalendarCheck",
        "tables": {
            "open_enrollment_events": None,  # None = all columns
            "benefit_plans": None,
            "benefit_plan_options": None,
            "plan_eligibility_rules": None,
            "benefit_enrollments": None,
            "employees": ["employee_id", "client_id", "employee_number", "employment_type", "employment_status", "hire_date", "is_benefits_eligible", "region_id", "department_id", "salary_band_id"],
            "dependents": None,
            "dependent_enrollments": None,
        },
    },
    {
        "app_id": "claims-analytics",
        "app_name": "Claims Analytics & Reporting",
        "description": "Tracks and analyzes benefit claims data for cost management, carrier performance, and utilization reporting.",
        "icon": "BarChart3",
        "tables": {
            "benefit_claims": None,
            "benefit_enrollments": ["enrollment_id", "employee_id", "plan_id", "option_id", "enrollment_status", "effective_date", "termination_date"],
            "benefit_plans": ["plan_id", "client_id", "plan_name", "plan_type", "plan_year", "carrier_name"],
            "benefit_plan_options": ["option_id", "plan_id", "coverage_level", "employee_cost_per_period", "employer_cost_per_period", "deductible_amount", "oop_max", "currency_code"],
            "employees": ["employee_id", "client_id", "region_id", "department_id", "salary_band_id"],
            "clients": ["client_id", "client_name", "industry"],
        },
    },
    {
        "app_id": "aca-compliance",
        "app_name": "ACA Compliance & Reporting",
        "description": "Supports Affordable Care Act compliance including ALE determination, 1094-C/1095-C reporting, and affordability tracking.",
        "icon": "ShieldCheck",
        "tables": {
            "clients": ["client_id", "client_name", "country_code", "is_active"],
            "regions": None,
            "employees": ["employee_id", "client_id", "employment_type", "employment_status", "hire_date", "termination_date", "is_benefits_eligible", "region_id"],
            "benefit_plans": ["plan_id", "client_id", "plan_name", "plan_type", "plan_year", "is_active"],
            "plan_eligibility_rules": None,
            "benefit_enrollments": ["enrollment_id", "employee_id", "plan_id", "enrollment_status", "effective_date", "termination_date"],
            "benefit_plan_options": ["option_id", "plan_id", "coverage_level", "employee_cost_per_period"],
            "salary_bands": None,
        },
    },
    {
        "app_id": "benefits-cost-analysis",
        "app_name": "Benefits Cost Analysis",
        "description": "Analyzes employer and employee benefit costs by plan, department, region, and salary tier for budget planning.",
        "icon": "DollarSign",
        "tables": {
            "benefit_plan_options": None,
            "benefit_plans": None,
            "benefit_enrollments": None,
            "employees": ["employee_id", "client_id", "region_id", "department_id", "salary_band_id", "employment_type"],
            "departments": None,
            "regions": ["region_id", "client_id", "region_name", "country_code"],
            "salary_bands": None,
            "clients": ["client_id", "client_name", "industry"],
        },
    },
    {
        "app_id": "dependent-management",
        "app_name": "Dependent & Family Coverage",
        "description": "Manages dependent eligibility, enrollment, age-out tracking, and family coverage tier validation.",
        "icon": "Users",
        "tables": {
            "dependents": None,
            "dependent_enrollments": None,
            "benefit_enrollments": ["enrollment_id", "employee_id", "plan_id", "option_id", "enrollment_status", "effective_date", "termination_date"],
            "benefit_plan_options": ["option_id", "plan_id", "coverage_level"],
            "employees": ["employee_id", "client_id", "employee_number"],
        },
    },
    {
        "app_id": "workforce-benefits-overview",
        "app_name": "Workforce Benefits Overview",
        "description": "Executive dashboard providing headcount, enrollment rates, and regional breakdowns for HR leadership.",
        "icon": "LayoutDashboard",
        "tables": {
            "clients": None,
            "regions": None,
            "departments": None,
            "employees": None,
            "benefit_enrollments": ["enrollment_id", "employee_id", "plan_id", "enrollment_status", "effective_date"],
            "benefit_plans": ["plan_id", "client_id", "plan_name", "plan_type", "plan_year"],
        },
    },
]


@router.get("/applications")
async def list_applications():
    result = []
    for app in _APPLICATIONS:
        table_count = len(app["tables"])
        col_count = 0
        for tbl_name, cols in app["tables"].items():
            if cols is None:
                # All columns — look up from schema
                for t in _MOCK_SCHEMA["tables"]:
                    if t["table_name"] == tbl_name:
                        col_count += len(t["columns"])
                        break
            else:
                col_count += len(cols)
        result.append({
            "app_id": app["app_id"],
            "app_name": app["app_name"],
            "description": app["description"],
            "icon": app["icon"],
            "table_count": table_count,
            "column_count": col_count,
        })
    return {"applications": result}


@router.get("/applications/{app_id}")
async def get_application(app_id: str):
    app = None
    for a in _APPLICATIONS:
        if a["app_id"] == app_id:
            app = a
            break
    if not app:
        return {"error": f"Application '{app_id}' not found"}

    tables_detail = []
    for tbl_name, col_filter in app["tables"].items():
        for t in _MOCK_SCHEMA["tables"]:
            if t["table_name"] == tbl_name:
                if col_filter is None:
                    columns = t["columns"]
                else:
                    columns = [c for c in t["columns"] if c["name"] in col_filter]
                fks = [fk for fk in t.get("foreign_keys", []) if col_filter is None or fk["column"] in col_filter]
                tables_detail.append({
                    "table_name": tbl_name,
                    "description": t["description"],
                    "columns": columns,
                    "foreign_keys": fks,
                    "column_count": len(columns),
                    "has_pii": any(c["is_pii"] for c in columns),
                })
                break

    return {
        "app_id": app["app_id"],
        "app_name": app["app_name"],
        "description": app["description"],
        "icon": app["icon"],
        "tables": tables_detail,
    }


@router.get("/tables/{table_name}/columns/{column_name}/usage")
async def get_column_usage(table_name: str, column_name: str):
    """Return all applications that use a given column."""
    using_apps = []
    for app in _APPLICATIONS:
        tbl_cols = app["tables"].get(table_name)
        if tbl_cols is None and table_name not in app["tables"]:
            continue
        # tbl_cols is None means "all columns" — column is included
        if tbl_cols is None or column_name in tbl_cols:
            using_apps.append({
                "app_id": app["app_id"],
                "app_name": app["app_name"],
                "description": app["description"],
                "icon": app["icon"],
            })
    return {
        "table_name": table_name,
        "column_name": column_name,
        "applications": using_apps,
    }


@router.get("/tables")
async def list_tables():
    return {
        "schema_name": _MOCK_SCHEMA["schema_name"],
        "tables": [
            {
                "table_name": t["table_name"],
                "description": t["description"],
                "column_count": len(t["columns"]),
                "has_pii": any(c["is_pii"] for c in t["columns"]),
            }
            for t in _MOCK_SCHEMA["tables"]
        ],
    }


@router.get("/tables/{table_name}")
async def get_table(table_name: str):
    for t in _MOCK_SCHEMA["tables"]:
        if t["table_name"] == table_name:
            return t
    return {"error": f"Table '{table_name}' not found"}


@router.get("/tables/{table_name}/columns")
async def get_columns(table_name: str):
    for t in _MOCK_SCHEMA["tables"]:
        if t["table_name"] == table_name:
            return {"table_name": table_name, "columns": t["columns"]}
    return {"error": f"Table '{table_name}' not found"}


@router.get("/tables/{table_name}/columns/{column_name}/metadata")
async def get_column_metadata(table_name: str, column_name: str):
    key = f"{table_name}.{column_name}"
    meta = _COLUMN_METADATA.get(key)
    if meta:
        return {"table_name": table_name, "column_name": column_name, **meta}
    # Return a basic fallback for columns without rich metadata
    for t in _MOCK_SCHEMA["tables"]:
        if t["table_name"] == table_name:
            for c in t["columns"]:
                if c["name"] == column_name:
                    return {
                        "table_name": table_name,
                        "column_name": column_name,
                        "business_name": column_name.replace("_", " ").title(),
                        "business_description": c["description"],
                        "valid_values": None,
                        "sample_values": None,
                        "formula": None,
                        "business_rules": [],
                        "lineage": None,
                        "used_in_metrics": [],
                        "relationships": [],
                    }
    return {"error": f"Column '{table_name}.{column_name}' not found"}


@router.put("/tables/{table_name}/columns/{column_name}/metadata")
async def update_column_metadata(table_name: str, column_name: str, body: dict):
    key = f"{table_name}.{column_name}"
    # Verify the column exists in the schema
    found = False
    for t in _MOCK_SCHEMA["tables"]:
        if t["table_name"] == table_name:
            for c in t["columns"]:
                if c["name"] == column_name:
                    found = True
                    break
            break
    if not found:
        return {"error": f"Column '{table_name}.{column_name}' not found"}

    allowed_fields = {
        "business_name", "business_description", "valid_values",
        "sample_values", "formula", "business_rules", "lineage",
        "used_in_metrics", "relationships",
    }
    ver = _allocate_version()
    for field in allowed_fields:
        if field in body:
            _apply_field_update(key, table_name, column_name, field, body[field], "manual", ver)
    _save_metadata()

    return {"table_name": table_name, "column_name": column_name, **_COLUMN_METADATA[key]}


# ── Version history endpoints ──────────────────────────────────────────

@router.get("/tables/{table_name}/columns/{column_name}/history")
async def get_column_history(table_name: str, column_name: str):
    """Return change history grouped by version, newest first."""
    entries = [
        h for h in _METADATA_HISTORY
        if h["table_name"] == table_name and h["column_name"] == column_name
    ]
    # Group by version
    version_map: Dict[int, List[Dict]] = {}
    for h in entries:
        ver = h.get("version", 0)
        version_map.setdefault(ver, []).append(h)
    # Build grouped list sorted by version desc
    versions = []
    for ver in sorted(version_map.keys(), reverse=True):
        changes = version_map[ver]
        changes.sort(key=lambda x: x["id"])
        versions.append({
            "version": ver,
            "timestamp": changes[0]["timestamp"],
            "source": changes[0]["source"],
            "changes": changes,
        })
    return {"table_name": table_name, "column_name": column_name, "versions": versions}


@router.post("/tables/{table_name}/columns/{column_name}/revert")
async def revert_column_change(table_name: str, column_name: str, body: dict):
    """Revert a specific history entry by its id — restores the old value."""
    history_id = body.get("history_id")
    if not history_id:
        return {"error": "history_id is required"}

    entry = None
    for h in _METADATA_HISTORY:
        if h["id"] == history_id and h["table_name"] == table_name and h["column_name"] == column_name:
            entry = h
            break
    if not entry:
        return {"error": f"History entry {history_id} not found for {table_name}.{column_name}"}

    key = f"{table_name}.{column_name}"
    # Revert: apply the old value without creating a new version
    existing = _COLUMN_METADATA.get(key, {})
    existing[entry["field"]] = copy.deepcopy(entry["old_value"])
    _COLUMN_METADATA[key] = existing
    _save_metadata()

    return {"table_name": table_name, "column_name": column_name, "reverted_field": entry["field"], **_COLUMN_METADATA[key]}


@router.post("/tables/{table_name}/columns/{column_name}/history/delete")
async def delete_history_entries(table_name: str, column_name: str, body: dict):
    """Delete specific history entries by their ids."""
    global _METADATA_HISTORY
    ids_to_delete = body.get("history_ids", [])
    if not ids_to_delete:
        return {"error": "history_ids is required (list of ids)"}
    before = len(_METADATA_HISTORY)
    _METADATA_HISTORY = [
        h for h in _METADATA_HISTORY
        if not (h["id"] in ids_to_delete and h["table_name"] == table_name and h["column_name"] == column_name)
    ]
    deleted = before - len(_METADATA_HISTORY)
    _save_history()
    # Return grouped versions
    remaining = [h for h in _METADATA_HISTORY if h["table_name"] == table_name and h["column_name"] == column_name]
    version_map: Dict[int, List[Dict]] = {}
    for h in remaining:
        ver = h.get("version", 0)
        version_map.setdefault(ver, []).append(h)
    versions = []
    for ver in sorted(version_map.keys(), reverse=True):
        changes = version_map[ver]
        changes.sort(key=lambda x: x["id"])
        versions.append({
            "version": ver,
            "timestamp": changes[0]["timestamp"],
            "source": changes[0]["source"],
            "changes": changes,
        })
    return {"deleted": deleted, "versions": versions}


# ── Impact Analysis ────────────────────────────────────────────────────

_IMPACT_SYSTEM_PROMPT = """\
You are a data governance analyst. You assess the impact of proposed metadata \
changes on applications that share the same data column.

You will receive:
1. The column being changed (table.column)
2. The CURRENT metadata for that column
3. The PROPOSED changes (field -> new value)
4. A list of OTHER applications that also use this column, with their descriptions

Your job is to evaluate whether the proposed changes could cause problems for \
the other applications and provide a risk assessment.

Return a JSON object:
{{
  "risk_level": "safe" | "warning" | "critical",
  "summary": "One-sentence overall assessment",
  "impacts": [
    {{
      "app_name": "Name of affected app",
      "concern": "What could go wrong for this app",
      "severity": "low" | "medium" | "high"
    }}
  ],
  "recommendations": ["actionable suggestion 1", "..."]
}}

Guidelines:
- "safe" = no meaningful risk to other apps
- "warning" = potential concerns that should be reviewed
- "critical" = changes that are very likely to break or mislead other apps
- Consider: will changing business rules affect how other apps interpret this data?
- Consider: will changing valid values break validation in other apps?
- Consider: will changing the formula/derivation cause inconsistent calculations?
- Consider: will renaming the business name confuse other app users?
- If there are NO other apps using this column, always return "safe".
- Return ONLY the JSON object, no markdown code fences.
"""


@router.post("/impact-analysis")
async def impact_analysis(body: dict):
    table_name = body.get("table_name", "")
    column_name = body.get("column_name", "")
    proposed_changes = body.get("proposed_changes", {})
    current_app_id = body.get("current_app_id", "")

    if not table_name or not column_name or not proposed_changes:
        return {"error": "table_name, column_name, and proposed_changes are required"}

    # Get current metadata
    key = f"{table_name}.{column_name}"
    current_meta = _COLUMN_METADATA.get(key, {})

    # Find other apps using this column (exclude current app)
    other_apps = []
    for app in _APPLICATIONS:
        if app["app_id"] == current_app_id:
            continue
        tbl_cols = app["tables"].get(table_name)
        if tbl_cols is None and table_name not in app["tables"]:
            continue
        if tbl_cols is None or column_name in tbl_cols:
            other_apps.append({
                "app_name": app["app_name"],
                "description": app["description"],
            })

    # If no other apps use this column, it's safe
    if not other_apps:
        return {
            "risk_level": "safe",
            "summary": "No other applications use this column. Safe to update.",
            "impacts": [],
            "recommendations": [],
        }

    # Build the prompt for GPT-4o
    user_msg = json.dumps({
        "column": f"{table_name}.{column_name}",
        "current_metadata": current_meta,
        "proposed_changes": proposed_changes,
        "other_applications": other_apps,
    }, indent=2)

    client = _get_openai()
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _IMPACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Impact analysis: failed to parse LLM response: %s", raw[:500])
        return {
            "risk_level": "warning",
            "summary": "Could not analyze impact — AI response was invalid.",
            "impacts": [],
            "recommendations": ["Review the change manually before applying."],
        }

    return {
        "risk_level": parsed.get("risk_level", "warning"),
        "summary": parsed.get("summary", ""),
        "impacts": parsed.get("impacts", []),
        "recommendations": parsed.get("recommendations", []),
    }


# ── Natural-language metadata update ──────────────────────────────────

_NL_SYSTEM_PROMPT = """\
You are an assistant that interprets natural language instructions about database \
column metadata and converts them into structured updates.

The schema has these tables and columns:
{columns_list}

Each column can have these metadata fields:
- business_name (string)
- business_description (string)
- valid_values (list of strings or null)
- sample_values (list of strings or null)
- formula (string or null)
- business_rules (list of strings)
- used_in_metrics (list of strings)
- relationships (list of strings)
- lineage (object with keys: source_system, load_frequency, transformation — or null)

Given a natural language instruction, return a JSON object with:
{{
  "updates": [
    {{
      "table_name": "the_table",
      "column_name": "the_column",
      "fields": {{
        "field_name": "new_value"
      }}
    }}
  ],
  "explanation": "Brief summary of what you understood and changed"
}}

Rules:
- Update ALL fields that are logically affected by the user's instruction, not just the one \
explicitly mentioned. For example, if the user says "add 5% government tax to employer cost", \
you should update:
  * formula — to include the tax calculation
  * business_rules — append a rule about the tax (e.g. "5% government tax applied to employer cost")
  * business_description — if the meaning of the column changes, update the description
  * used_in_metrics — if the change affects which metrics use this column
  * relationships — if the change introduces a dependency on another column
  Think holistically: a single business change often affects formula, rules, and description together.
- If the user refers to a column ambiguously, pick the most likely match
- If the column does not exist, return {{"updates": [], "explanation": "Column not found: ..."}}
- If the user message starts with "[Currently selected column: table.column]", treat that as \
the default target column when the instruction is ambiguous (e.g. "change the date format" \
should apply to the selected column).
- If the user message includes "[Current metadata: ...]", use that to understand the column's \
existing formula, business rules, description, etc. When the user says something like \
"add 5% tax" or "multiply by 1.05", apply the change to the EXISTING formula. For example, \
if the current formula is "Total annual premium - annual_employee_cost" and the user says \
"add 5% government tax", the new formula should be "(Total annual premium - annual_employee_cost) * 1.05", \
NOT "column_name * 1.05".
- For list fields (business_rules, used_in_metrics, valid_values, relationships, etc), always return \
  the COMPLETE desired list as the new value. Include all existing items that should be kept, \
  plus any new items being added, minus any items being removed. Do NOT use partial lists or \
  append markers — always provide the full final list so it cleanly replaces the old one.
- Return ONLY the JSON object, no markdown code fences.
"""


def _build_columns_list() -> str:
    lines = []
    for t in _MOCK_SCHEMA["tables"]:
        for c in t["columns"]:
            lines.append(f"  {t['table_name']}.{c['name']}")
    return "\n".join(lines)


_openai_client = None


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


@router.post("/nl-preview")
async def nl_preview(body: dict):
    """Parse NL instruction and return proposed changes + impact analysis WITHOUT applying."""
    instruction = body.get("instruction", "").strip()
    if not instruction:
        return {"error": "No instruction provided"}

    # If the frontend tells us which column is selected, prepend context + full metadata
    context = body.get("context")
    user_message = instruction
    if context and context.get("table_name") and context.get("column_name"):
        tbl = context["table_name"]
        col = context["column_name"]
        meta_key = f"{tbl}.{col}"
        current_meta = _COLUMN_METADATA.get(meta_key, {})
        meta_json = json.dumps(current_meta, indent=2, default=str) if current_meta else "No metadata"
        user_message = (
            f"[Currently selected column: {tbl}.{col}]\n"
            f"[Current metadata: {meta_json}]\n\n"
            f"{instruction}"
        )

    client = _get_openai()
    system = _NL_SYSTEM_PROMPT.format(columns_list=_build_columns_list())

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("NL preview: failed to parse LLM response: %s", raw[:500])
        return {"error": "Failed to parse AI response", "raw": raw}

    updates = parsed.get("updates", [])
    explanation = parsed.get("explanation", "")

    allowed_fields = {
        "business_name", "business_description", "valid_values",
        "sample_values", "formula", "business_rules", "lineage",
        "used_in_metrics", "relationships",
    }

    # Build preview diffs (old vs new) without applying
    previews = []
    for upd in updates:
        tbl = upd.get("table_name", "")
        col = upd.get("column_name", "")
        fields = upd.get("fields", {})
        key = f"{tbl}.{col}"

        # Verify column exists
        found = False
        for t in _MOCK_SCHEMA["tables"]:
            if t["table_name"] == tbl:
                for c in t["columns"]:
                    if c["name"] == col:
                        found = True
                        break
                break
        if not found:
            continue

        existing = _COLUMN_METADATA.get(key, {})
        field_diffs = []
        resolved_fields = {}
        for field_name, value in fields.items():
            if field_name not in allowed_fields:
                continue
            old_value = existing.get(field_name)
            resolved_fields[field_name] = value
            field_diffs.append({
                "field": field_name,
                "old_value": copy.deepcopy(old_value),
                "new_value": value,
            })
        if field_diffs:
            previews.append({
                "table_name": tbl,
                "column_name": col,
                "fields": resolved_fields,
                "diffs": field_diffs,
            })

    # Run impact analysis for each affected column
    impact_results = []
    for prev in previews:
        tbl = prev["table_name"]
        col = prev["column_name"]
        # Find other apps using this column
        other_apps = []
        for app in _APPLICATIONS:
            tbl_cols = app["tables"].get(tbl)
            if tbl_cols is None and tbl not in app["tables"]:
                continue
            if tbl_cols is None or col in tbl_cols:
                other_apps.append({"app_name": app["app_name"], "description": app["description"]})
        if not other_apps:
            impact_results.append({
                "table_name": tbl, "column_name": col,
                "risk_level": "safe",
                "summary": "No other applications use this column.",
                "impacts": [], "recommendations": [],
            })
            continue
        # Call LLM for impact
        key = f"{tbl}.{col}"
        current_meta = _COLUMN_METADATA.get(key, {})
        impact_msg = json.dumps({
            "column": f"{tbl}.{col}",
            "current_metadata": current_meta,
            "proposed_changes": prev["fields"],
            "other_applications": other_apps,
        }, indent=2)
        try:
            impact_resp = client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": _IMPACT_SYSTEM_PROMPT},
                    {"role": "user", "content": impact_msg},
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            impact_parsed = json.loads(impact_resp.choices[0].message.content)
            impact_results.append({
                "table_name": tbl, "column_name": col,
                "risk_level": impact_parsed.get("risk_level", "warning"),
                "summary": impact_parsed.get("summary", ""),
                "impacts": impact_parsed.get("impacts", []),
                "recommendations": impact_parsed.get("recommendations", []),
            })
        except Exception:
            impact_results.append({
                "table_name": tbl, "column_name": col,
                "risk_level": "warning",
                "summary": "Could not analyze impact.",
                "impacts": [], "recommendations": ["Review manually."],
            })

    return {
        "explanation": explanation,
        "previews": previews,
        "impact": impact_results,
        "preview_count": len(previews),
    }


@router.post("/nl-apply")
async def nl_apply(body: dict):
    """Apply a previously previewed set of NL changes."""
    previews = body.get("previews", [])
    if not previews:
        return {"error": "No previews to apply"}

    applied = []
    for prev in previews:
        tbl = prev.get("table_name", "")
        col = prev.get("column_name", "")
        fields = prev.get("fields", {})
        key = f"{tbl}.{col}"

        # Verify column exists
        found = False
        for t in _MOCK_SCHEMA["tables"]:
            if t["table_name"] == tbl:
                for c in t["columns"]:
                    if c["name"] == col:
                        found = True
                        break
                break
        if not found:
            continue

        ver = _allocate_version()
        for field_name, value in fields.items():
            _apply_field_update(key, tbl, col, field_name, value, "nl-update", ver)
        applied.append({"table_name": tbl, "column_name": col, "updated_fields": list(fields.keys())})

    if applied:
        _save_metadata()

    return {"applied": applied, "update_count": len(applied)}
