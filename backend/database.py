import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

if not url or not key:
    print("Warning: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")

# Use Service Key for backend operations (admin privileges) to bypass RLS when necessary
# For user-specific operations, we might want to pass the user's JWT
supabase: Client = create_client(url, key)

def get_supabase() -> Client:
    return supabase
