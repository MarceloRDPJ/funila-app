import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase: Client = None

def get_config():
    url = os.environ.get("SUPABASE_URL")
    # Prioritize SERVICE_KEY for backend operations, but allow ANON_KEY as fallback
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    return url, key

def init_supabase():
    global supabase
    url, key = get_config()

    if not url or not key:
        print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_KEY/SUPABASE_KEY not set. Database operations will fail.")
        return None
    try:
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"CRITICAL: Failed to initialize Supabase client: {e}")
        return None

# Try initializing on module load
init_supabase()

def get_supabase() -> Client:
    global supabase
    if supabase is None:
        # Retry initialization in case env vars were set late
        if init_supabase() is None:
            raise RuntimeError("Supabase client is not initialized due to missing credentials.")
    return supabase
