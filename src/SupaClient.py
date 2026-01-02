import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
# Try to get service role key, fallback to regular key if not set
service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or key

# Warn if service role key is not set or is the same as regular key
# if not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
#     print("WARNING: SUPABASE_SERVICE_ROLE_KEY not set. Using regular key for admin operations.")
#     print("This may cause role update failures. Please set SUPABASE_SERVICE_ROLE_KEY in your .env file.")
# elif service_role_key == key:
#     print("WARNING: SUPABASE_SERVICE_ROLE_KEY is the same as SUPABASE_KEY.")
#     print("Please use the service_role key (secret) from Supabase dashboard for admin operations.")

supabase: Client = create_client(url, key)
# Admin client with service role key for admin operations
supabase_admin: Client = create_client(url, service_role_key)

def get_supabase() -> Client:
    return supabase

def get_supabase_admin() -> Client:
    return supabase_admin