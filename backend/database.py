import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configuradas.")

supabase: Client = create_client(url, key)

def get_supabase() -> Client:
    return supabase
