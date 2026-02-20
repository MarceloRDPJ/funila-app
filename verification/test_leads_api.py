import sys
import os
from cryptography.fernet import Fernet
from unittest.mock import patch

# Set dummy env vars to avoid RuntimeError in database.py
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "mock_key"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock
# We don't import get_supabase here to patch it, we patch where it is used.

client = TestClient(app)

# Mock Supabase
mock_supabase = MagicMock()
mock_table = MagicMock()
mock_supabase.table.return_value = mock_table
# Mock insert/update responses
mock_table.insert.return_value.execute.return_value.data = [{"id": "mock_id"}]
mock_table.update.return_value.eq.return_value.execute.return_value.data = [{"id": "mock_id"}]
mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"plan": "solo", "email": "x", "whatsapp": ""}

def test_partial_lead_abandoned():
    """Verify partial leads are saved as 'abandoned' and device captured"""
    payload = {
        "client_id": "mock_client_id",
        "link_id": "mock_link_id",
        "last_step": "step_1",
        "utm_data": {},
        "name": "Test User",
        "phone": "123456789"
    }
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"}

    # Patch get_supabase inside routes.leads module
    with patch('routes.leads.get_supabase', return_value=mock_supabase):
        response = client.post("/leads/partial", json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Failed with {response.status_code}: {response.text}")

    assert response.status_code == 200

    # Verify mock call arguments
    calls = mock_table.insert.call_args_list

    found = False
    for call in calls:
        args, _ = call
        data = args[0]
        if isinstance(data, dict) and data.get("status") == "abandoned":
            found = True
            assert data["device_type"] == "mobile"
            assert data["step_reached"] == 1
            print("Verified: status='abandoned', device_type='mobile', step_reached=1")
            break

    if not found:
        print("Failed to find insert call with status='abandoned'")
        print("Calls:", calls)
        assert False

if __name__ == "__main__":
    try:
        test_partial_lead_abandoned()
        print("Verification Passed!")
    except Exception as e:
        print(f"Verification Failed: {e}")
        exit(1)
