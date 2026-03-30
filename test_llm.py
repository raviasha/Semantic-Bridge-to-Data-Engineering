import urllib.request, json

# 1. Start an interview
data = json.dumps({"title": "Test LLM Integration", "description": "Testing GPT-4o"}).encode()
req = urllib.request.Request("http://localhost:8002/api/interviews", data=data, headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read().decode())
iid = resp["interview_id"]
print("Interview created:", iid)

# 2. Send a message
msg = json.dumps({"message": "I need to calculate the medical enrollment rate by department for our company"}).encode()
req2 = urllib.request.Request("http://localhost:8002/api/interviews/%s/messages" % iid, data=msg, headers={"Content-Type": "application/json"})
resp2 = json.loads(urllib.request.urlopen(req2, timeout=30).read().decode())
print("Status:", resp2["status"])
print("Confidence:", resp2["confidence_score"])
print("Entities:", len(resp2.get("entities", [])))
print("---RESPONSE---")
print(resp2["assistant_turn"]["content"][:500])
