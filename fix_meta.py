import json

path = "/Users/rampetaravishankar/Desktop/Data Engineering-Semantic Bridge/backend/data/column_metadata.json"
with open(path) as f:
    meta = json.load(f)

key = "benefit_plan_options.annual_employer_cost"
meta[key]["business_rules"] = [
    "Employer contribution varies by client, plan, and coverage level",
    "ACA affordability test: employee self-only contribution must be \u2264 9.12% of household income (2025 threshold)",
    "Some employers use defined contribution model (flat $ amount regardless of plan)",
]
meta[key]["used_in_metrics"] = [
    "Per-employee-per-month (PEPM) cost",
    "Total benefits liability",
    "Employer cost trend YoY",
]
meta[key]["formula"] = "Total annual premium - annual_employee_cost"
meta[key]["business_description"] = "The total annual amount the employer pays for this coverage option. Key component of benefits expense budgeting."

with open(path, "w") as f:
    json.dump(meta, f, indent=2)

print("All fields cleaned")
