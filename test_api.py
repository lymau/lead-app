from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def run_tests():
    print("[TEST] 1. Testing GET /health...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resp.json() == {"status": "ok", "service": "Lead App API"}
    print("       SUCCESS: /health OK")

    print("[TEST] 2. Testing GET /auth/users...")
    resp = client.get("/auth/users")
    assert resp.status_code == 200
    users = resp.json()
    print(f"       SUCCESS: Found {len(users)} users.")
    sample_user = users[0] if users else "Ade Frianche"

    print(f"[TEST] 3. Testing GET /leads?username={sample_user}...")
    resp = client.get(f"/leads?username={sample_user}")
    print(f"       Status: {resp.status_code}")
    if resp.status_code == 200:
        leads_data = resp.json().get("data", [])
        print(f"       SUCCESS: Retrieved {len(leads_data)} leads for user {sample_user}.")
    else:
        print(f"       Response: {resp.text}")

    print("[TEST] 4. Testing GET /master/companies...")
    resp = client.get("/master/companies")
    assert resp.status_code == 200
    print(f"       SUCCESS: Found {len(resp.json())} companies.")

    print("[TEST] 5. Testing GET /notifications/registered-emails...")
    resp = client.get("/notifications/registered-emails")
    assert resp.status_code == 200
    print(f"       SUCCESS: Found {len(resp.json())} registered emails.")

    print("[TEST] ALL SMOKE TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
