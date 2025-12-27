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
    # Capture the new name fields from your form
    first_name = data.get('first_name') 
    last_name = data.get('last_name')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    supabase = get_supabase()
    try:
        # Pass the names into the 'data' dictionary inside 'options'
        res = supabase.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {
                "data": {
                    "first_name": first_name,
                    "last_name": last_name
                }
            }
        })
        return jsonify({"message": "Registration successful! Please check your email. (implemented later)"})
    except Exception as e:
        print(f"Signup error: {e}")
        return jsonify({"error": str(e)}), 400
    

@api.route('/get-rfq/<int:rfq_id>', methods=['GET'])
@login_required
def get_rfq(user, rfq_id):
    """Fetches a single RFQ and its parts for editing."""
    supabase = get_supabase()
    try:
        # We ensure the user can only fetch their own RFQ
        res = supabase.table("RFQ-Tracker") \
            .select("*, Part_details(*)") \
            .eq("id", rfq_id) \
            .eq("created_by", user.id) \
            .single() \
            .execute()
        
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@api.route('/make-rfq-entry', methods=['POST'])
@login_required
def make_entry(user):
    supabase = get_supabase()
    data = request.get_json()
    
    # Check if we are updating or inserting
    existing_rfq_id = data.get('id') 

    try:
        header_data = {
            "RFQ-no": data.get('rfq_no'),
            "Company_name": data.get('company_name'),
            "Sales_person": data.get('sales_person'),
            "Customer_name": data.get('customer_name'),
            "created_by": user.id
        }
        
        if existing_rfq_id:
            # --- UPDATE MODE ---
            # 1. Update Header
            supabase.table("RFQ-Tracker").update(header_data).eq("id", existing_rfq_id).execute()
            # 2. Delete existing parts (to refresh with the new list)
            supabase.table("Part_details").delete().eq("rfq_id", existing_rfq_id).execute()
            new_rfq_id = existing_rfq_id
        else:
            # --- INSERT MODE ---
            header_res = supabase.table("RFQ-Tracker").insert(header_data).execute()
            if not header_res.data:
                return jsonify({"error": "Failed to create RFQ Header"}), 500
            new_rfq_id = header_res.data[0]['id']

        # --- PROCESS PARTS (Same for both modes) ---
        items_to_insert = []
        for item in data.get('items', []):
            items_to_insert.append({
                "rfq_id": new_rfq_id,
                "RFQ-part-no": item.get('rfq_part_no'),
                "Quoted-part-no": item.get('quoted_part_no'),
                "Supplier": item.get('supplier'),
                "Date Code": item.get('date_code') or None,
                "RFQ Qty": item.get('rfq_qty'),
                "Quoted Qty": item.get('quoted_qty'),
                "Make": item.get('make'),
                "Lead": item.get('lead_time'),
                "Unit$": item.get('unit_price_usd'),
                "Unit₹": item.get('unit_price_inr'),
                "Remarks": item.get('remarks')
            })

        if items_to_insert:
            supabase.table("Part_details").insert(items_to_insert).execute()

        return jsonify({"success": True, "rfq_id": new_rfq_id}), 201

    except Exception as e:
        print(f"Error saving RFQ: {e}")
        return jsonify({"error": str(e)}), 500

@api.route('/delete-rfq/<int:rfq_id>', methods=['DELETE'])
@login_required
def delete_rfq(user, rfq_id):
    supabase = get_supabase()
    try:
        # Step 1: Manually delete the children (Part_details) first
        supabase.table("Part_details").delete().eq("rfq_id", rfq_id).execute()
        
        # Step 2: Now delete the parent (RFQ-Tracker)
        supabase.table("RFQ-Tracker").delete().eq("id", rfq_id).eq("created_by", user.id).execute()
        
        return jsonify({"success": True, "message": "RFQ and parts deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api.route('/list-rfq-entry', methods=['GET'])
@login_required
def list_entry(user):
    supabase = get_supabase()
    
    try:
        # Fetch RFQs created by this user
        # The 'select' string tells Supabase to join Part_details automatically
        res = supabase.table("RFQ-Tracker") \
            .select('*, Part_details(*)') \
            .eq("created_by", user.id) \
            .order("created_at", desc=True) \
            .execute()

        return jsonify({
            "success": True,
            "data": res.data
        }), 200

    except Exception as e:
        print(f"Error fetching RFQs: {e}")
        return jsonify({"error": str(e)}), 500