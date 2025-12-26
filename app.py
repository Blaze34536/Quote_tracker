from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from flask_wtf.csrf import CSRFProtect, generate_csrf
from src.config import Config
from src.auth.utils import login_required
from src.SupaClient import get_supabase

app = Flask(__name__)
app.config.from_object(Config)

# Make sure you have a SECRET_KEY in your Config
# app.config['SECRET_KEY'] should be set to a random string
# In production, use environment variable: os.environ.get('SECRET_KEY')

csrf = CSRFProtect(app)

@app.route("/")
@login_required
def rfq(user):
    return render_template("rfqEditor2.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout(user):
    supabase = get_supabase()
    supabase.auth.sign_out()
    
    response = make_response(redirect(url_for('login')))
    response.set_cookie('access_token', '', expires=0)  # Clear the cookie
    return response

@app.route("/rfq-list")
@login_required
def rfq_list(user):
    return render_template("rfqList.html")

# Endpoint to get CSRF token
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

# API Routes for Authentication
@app.route('/api/login', methods=['POST'])
@csrf.exempt  # We'll handle CSRF manually for login
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
        
        # Also set CSRF token cookie (not HTTP-only, so JS can read it)
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
        return jsonify({"error": str(e)}), 401

@app.route('/api/signup', methods=['POST'])
@csrf.exempt  # Exempt signup from CSRF
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
        return jsonify({"error": str(e)}), 400

# Example of a protected API endpoint that requires CSRF
@app.route('/api/protected-action', methods=['POST'])
@login_required
def protected_action(user):
    # CSRF is automatically validated by Flask-WTF for POST requests
    data = request.get_json()
    # Your protected logic here
    return jsonify({"success": True, "message": "Action completed"})

if __name__ == "__main__":
    app.run(debug=True)