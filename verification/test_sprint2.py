import sys
import os
from cryptography.fernet import Fernet
from unittest.mock import patch, MagicMock

# Set dummy env vars
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "mock_key"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["META_APP_ID"] = "123456"
os.environ["META_APP_SECRET"] = "abcdef"

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from fastapi.testclient import TestClient
from main import app
from database import get_supabase
from dependencies import require_client

client = TestClient(app)

# Mock Supabase
mock_supabase = MagicMock()
mock_table = MagicMock()
mock_supabase.table.return_value = mock_table

# Override dependency
app.dependency_overrides[get_supabase] = lambda: mock_supabase
app.dependency_overrides[require_client] = lambda: {"client_id": "test_client", "role": "client"}

def test_meta_connect_url():
    response = client.get("/oauth/meta/connect")

    if response.status_code != 200:
        print(f"Meta Connect Failed: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "https://www.facebook.com/v19.0/dialog/oauth" in data["url"]
    assert "client_id=123456" in data["url"]
    print("Meta Connect URL verified.")

def test_get_creatives():
    # Mock creatives return
    mock_creatives = [{
        "id": "c1",
        "name": "Ad 1",
        "spend_cents": 1000,
        "leads_generated": 5,
        "external_id": "ext1"
    }]

    # Mock supabase response for creatives
    mock_creatives_res = MagicMock()
    mock_creatives_res.data = mock_creatives

    # Mock supabase response for leads
    mock_leads_res = MagicMock()
    mock_leads_res.data = [{"internal_score": 80, "creative_id": "c1"}]

    def table_side_effect(name):
        t = MagicMock()
        if name == "creatives":
            t.select.return_value.eq.return_value.execute.return_value = mock_creatives_res
        elif name == "leads":
            t.select.return_value.eq.return_value.execute.return_value = mock_leads_res
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch('routes.creatives.get_supabase', return_value=mock_supabase):
        response = client.get("/creatives")

        if response.status_code != 200:
            print(f"Get Creatives Failed: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert "creatives" in data
        assert len(data["creatives"]) == 1
        c = data["creatives"][0]
        assert c["avg_score"] == 80
        assert c["leads_generated"] == 1
        print("Get Creatives verified.")

if __name__ == "__main__":
    try:
        test_meta_connect_url()
        test_get_creatives()
        print("Sprint 2 Verification Passed!")
    except Exception as e:
        print(f"Verification Failed: {e}")
        exit(1)
