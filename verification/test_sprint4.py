import sys
import os
from cryptography.fernet import Fernet
from unittest.mock import patch, MagicMock

# Set dummy env vars
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "mock_key"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from fastapi.testclient import TestClient
from main import app
from database import get_supabase
from dependencies import require_master

client = TestClient(app)

# Mock Supabase
mock_supabase = MagicMock()
mock_table = MagicMock()
mock_supabase.table.return_value = mock_table

# Override dependency
app.dependency_overrides[get_supabase] = lambda: mock_supabase
app.dependency_overrides[require_master] = lambda: {"id": "master_id", "role": "master"}

def test_impersonation_flow():
    # Mock client fetch
    mock_client = {"id": "client_123", "email": "client@test.com"}
    mock_res = MagicMock()
    mock_res.data = mock_client

    mock_user_res = MagicMock()
    mock_user_res.data = [{"id": "user_123"}]

    def table_side_effect(name):
        t = MagicMock()
        if name == "clients":
            t.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_res
        elif name == "users":
            t.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_user_res
        elif name == "events":
            t.insert.return_value.execute.return_value = None
            return t
        return t

    mock_supabase.table.side_effect = table_side_effect

    # Ensure no external calls
    with patch('routes.admin.master.get_supabase', return_value=mock_supabase):
        response = client.post("/admin/master/impersonate/client_123")

    if response.status_code != 200:
        print(f"Impersonation Failed: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "redirect" in data
    print("Impersonation Flow Verified.")

if __name__ == "__main__":
    try:
        test_impersonation_flow()
        print("Sprint 4 Verification Passed!")
    except Exception as e:
        print(f"Verification Failed: {e}")
        exit(1)
