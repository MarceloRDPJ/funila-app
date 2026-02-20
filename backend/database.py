import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = None

if not url or not key:
    print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY not set. Database operations will fail.")
else:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Supabase client: {e}")

def get_supabase() -> Client:
    if supabase is None:
        raise RuntimeError("Supabase client is not initialized.")
    return supabase
