from flask import request, jsonify, redirect, url_for
from src.SupaClient import get_supabase
from functools import wraps

def get_current_user():
    """Fetches the auth user AND their custom profile role."""
    token = request.cookies.get('access_token')
    
    if not token:
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")

    if not token:
        return None

    supabase = get_supabase()
    try:
        res = supabase.auth.get_user(token)
        if not res or not res.user:
            return None
        
        user = res.user

        profile_res = supabase.table("profiles").select("role").eq("user_id", user.id).maybe_single().execute()

        user.role = profile_res.data["role"] if (profile_res.data and "role" in profile_res.data) else "user"
        
        return user
    except Exception as e:
        print(f"Error getting user with profile: {e}")
        return None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Now uses the function that attaches your custom role
        user = get_current_user()
        if not user:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login'))
        
        # This 'user' now has the correct .role (admin/sales) instead of 'authenticated'
        return f(user, *args, **kwargs)
    return wrapper

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if user.role not in allowed_roles:
                return jsonify({"error": f"Forbidden: {user.role} not in {allowed_roles}"}), 403

            return f(user, *args, **kwargs)
        return wrapper
    return decorator