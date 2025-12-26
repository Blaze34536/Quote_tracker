from flask import Blueprint, request, jsonify, make_response
from flask_wtf.csrf import CSRFProtect, generate_csrf
from src.auth.utils import login_required
from src.SupaClient import get_supabase

api = Blueprint('api', __name__, url_prefix='/api')

# Endpoint to get CSRF token
@api.route('/csrf-token', methods=['GET'])
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

# API Routes for Authentication
@api.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        response = make_response(jsonify({
            "success": True,
            "user": {
                "id": res.user.id,
                "email": res.user.email
            }
        }))
        
        # Set HTTP-only cookie with the access token
        response.set_cookie(
            'access_token', 
            res.session.access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=3600  # 1 hour
        )
        
        # Set CSRF token cookie
        response.set_cookie(
            'csrf_token',
            generate_csrf(),
            httponly=False,  # JS needs to read this
            secure=False,  # Set to True in production
            samesite='Lax',
            max_age=3600
        )
        
        return response
    except Exception as e:
        print(f"Login error: {e}")  # Debug logging
        return jsonify({"error": str(e)}), 401

@api.route('/signup', methods=['POST'])
def api_signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        return jsonify({"message": "Check your email for verification"})
    except Exception as e:
        print(f"Signup error: {e}")  # Debug logging
        return jsonify({"error": str(e)}), 400
