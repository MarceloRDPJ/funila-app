import httpx
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import MagicMock
from backend.routes import tracker, leads

# Ensure we are mocking the `get_supabase` function call inside the routes
mock_client = MagicMock()
mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "mock_id_123"}]
mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{"id": "mock_id_123"}] # fix chain for update
mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{"id": "mock_id_123"}] # fix chain for update link
mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
    "plan": "basic", "email": "test@test.com", "whatsapp": "551199999999", "id": "client_123"
}
mock_client.table.return_value.select.return_value.execute.return_value.data = [
    {"id": "f1", "field_key": "email"}, {"id": "f2", "field_key": "phone"}
]

# Monkeypatching logic
tracker.get_supabase = lambda: mock_client
leads.get_supabase = lambda: mock_client

client = TestClient(app)

def test_funnel_flow():
    print("Testing /funnel/event (Page View)")
    # 1. Page View
    res = client.post("/funnel/event", json={
        "session_id": "sess_123",
        "link_id": "link_123",
        "event_type": "page_view",
        "step": 1
    })
    # If 500, print error
    if res.status_code != 200:
        print(f"Error: {res.text}")
    print(f"Page View: {res.status_code} - {res.json()}")
    assert res.status_code == 200

    print("Testing /leads/partial")
    # 3. Partial Save
    res = client.post("/leads/partial", json={
        "client_id": "client_123",
        "link_id": "link_123",
        "session_id": "sess_123",
        "name": "Test User",
        "phone": "(11) 99999-9999",
        "utm_data": {}
    })
    if res.status_code != 200:
        print(f"Error: {res.text}")
    print(f"Partial Save: {res.status_code} - {res.json()}")
    assert res.status_code == 200
    lead_id = res.json().get("lead_id")

    print("Testing /leads (Final Submit)")
    # 4. Final Submit
    res = client.post("/leads", json={
        "client_id": "client_123",
        "link_id": "link_123",
        "lead_id": lead_id,
        "form_data": {
            "full_name": "Test User",
            "phone": "(11) 99999-9999",
            "email": "test@test.com",
            "cpf": "123.456.789-00"
        },
        "consent_given": True
    })
    if res.status_code != 200:
        print(f"Error: {res.text}")
    print(f"Final Submit: {res.status_code} - {res.json()}")
    assert res.status_code == 200

if __name__ == "__main__":
    try:
        test_funnel_flow()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
