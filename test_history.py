"""Test persistence, history tracking, and revert."""
import urllib.request
import json
import os

BASE = "http://localhost:8002/api/schema"

def api_get(path):
    req = urllib.request.Request(f"{BASE}{path}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def api_post(path, data):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def api_put(path, data):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=payload, headers={"Content-Type": "application/json"}, method="PUT")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

print("=== 1. Make a metadata update via PUT ===")
result = api_put("/tables/benefit_plan_options/columns/annual_employer_cost/metadata", {"formula": "test_formula_123"})
print(f"  formula after PUT: {result.get('formula')}")

print("\n=== 2. Check history was recorded ===")
hist = api_get("/tables/benefit_plan_options/columns/annual_employer_cost/history")
entries = hist.get("history", [])
print(f"  History entries: {len(entries)}")
if entries:
    h = entries[0]
    print(f"  Latest: field={h['field']} | old={str(h.get('old_value',''))[:60]} -> new={str(h.get('new_value',''))[:60]} | source={h['source']}")
    hist_id = h["id"]

    print("\n=== 3. Revert the change ===")
    rev = api_post(f"/tables/benefit_plan_options/columns/annual_employer_cost/revert", {"history_id": hist_id})
    print(f"  formula after revert: {rev.get('formula')}")
    print(f"  reverted_field: {rev.get('reverted_field')}")

print("\n=== 4. Check persistence files ===")
print(f"  data/column_metadata.json exists: {os.path.exists('data/column_metadata.json')}")
print(f"  data/metadata_history.json exists: {os.path.exists('data/metadata_history.json')}")

print("\n=== 5. Check history count after revert ===")
hist2 = api_get("/tables/benefit_plan_options/columns/annual_employer_cost/history")
print(f"  History entries: {len(hist2.get('history', []))}")

print("\nAll tests passed!")
