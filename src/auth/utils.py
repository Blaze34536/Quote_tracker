from flask import request, jsonify, redirect, url_for
from src.SupaClient import get_supabase
from functools import wraps

def get_current_user():
    token = request.cookies.get('access_token')
    
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")

    if not token:
        return None

    supabase = get_supabase()
    try:
        res = supabase.auth.get_user(token)
        return res.user if res else None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login'))  # Redirect to login page for web requests
        return f(user, *args, **kwargs)
    return wrapper