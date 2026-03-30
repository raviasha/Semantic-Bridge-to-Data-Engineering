"""Test enriched NL context — the formula problem."""
import urllib.request
import json

BASE = "http://localhost:8002/api/schema"

def api_post(path, data):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def api_get(path):
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

# First check current formula
meta = api_get("/tables/benefit_plan_options/columns/annual_employer_cost/metadata")
print(f"Current formula: {meta.get('formula')}")

# Now simulate the user saying "the govt has to be paid 5% tax so the employer cost should change accordingly"
result = api_post("/nl-update", {
    "instruction": "the govt has to be paid 5% tax so the employer cost should change accordingly",
    "context": {"table_name": "benefit_plan_options", "column_name": "annual_employer_cost"}
})
print(f"\nNL update explanation: {result.get('explanation')}")
print(f"Applied: {result.get('applied')}")

# Check what formula was set
meta2 = api_get("/tables/benefit_plan_options/columns/annual_employer_cost/metadata")
print(f"\nNew formula: {meta2.get('formula')}")

# Revert it back
hist = api_get("/tables/benefit_plan_options/columns/annual_employer_cost/history")
entries = hist.get("history", [])
# Find the formula change entry
for h in entries:
    if h["field"] == "formula" and h["source"] == "nl-update":
        print(f"\nReverting history entry {h['id']}...")
        rev = api_post(f"/tables/benefit_plan_options/columns/annual_employer_cost/revert", {"history_id": h["id"]})
        print(f"Formula after revert: {rev.get('formula')}")
        break
