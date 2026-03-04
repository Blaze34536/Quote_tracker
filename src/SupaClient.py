import os
from supabase import create_client, Client
from dotenv import load_dotenv
import sys 

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Load the .env from the bundle's internal path
load_dotenv(resource_path(".env"))

# Now these will work inside the EXE
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError(f"Supabase credentials missing. Looked in: {resource_path('.env')}")


supabase: Client = create_client(url, key)
supabase_admin: Client = create_client(url, key)

def get_supabase() -> Client:
    return supabase

def get_supabase_admin() -> Client:
    return supabase_admin