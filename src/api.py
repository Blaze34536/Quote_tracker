from flask import Blueprint, request, jsonify
from src.auth.utils import login_required
from src.SupaClient import get_supabase

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/make-rfq-entry', methods=['POST'])
@login_required
def make_entry(user):
    supabase = get_supabase()
    data = request.get_json()
    existing_rfq_id = data.get('id') 

    try:
        header_data = {
            "RFQ-no": data.get('rfq_no'),
            "Company_name": data.get('company_name'),
            "Sales_person": data.get('sales_person'),
            "Customer_name": data.get('customer_name'),
            "Customer_email": data.get('customer_email'),
            "Customer_phone": data.get('customer_phone'),
            "RFQ_purpose": data.get('rfq_purpose'),
            "Tentative_date": data.get('tentative_date') or None,
            "created_by": user.id
        }
        
        if existing_rfq_id:
            supabase.table("RFQ-Tracker").update(header_data).eq("id", existing_rfq_id).execute()
            supabase.table("Part_details").delete().eq("rfq_id", existing_rfq_id).execute()
            new_rfq_id = existing_rfq_id
        else:
            header_res = supabase.table("RFQ-Tracker").insert(header_data).execute()
            new_rfq_id = header_res.data[0]['id']

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
                "Source": item.get('source'),
                "Unit$": item.get('unit_price_usd'),
                "Unit₹": item.get('unit_price_inr'),
                "Freight": item.get('freight'),
                "Insurance": item.get('insurance'),
                "BCD": item.get('bcd'),
                "Bank": item.get('bank'),
                "Clearance": item.get('clearance'),
                "Margin": item.get('margin'),
                "Resale": item.get('resale'),
                "TP": item.get('tp'),
                "Remarks": item.get('remarks')
            })

        if items_to_insert:
            supabase.table("Part_details").insert(items_to_insert).execute()

        return jsonify({"success": True, "rfq_id": new_rfq_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/list-rfq-entry', methods=['GET'])
@login_required
def list_entry(user):
    supabase = get_supabase()
    try:
        query = supabase.table("RFQ-Tracker") \
            .select('*, Part_details(*)')
        
        if user.role != "admin":
            query = query.eq("created_by", user.id)
        
        res = query.order("created_at", desc=True).execute()
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/get-rfq/<int:rfq_id>', methods=['GET'])
@login_required
def get_rfq(user, rfq_id):
    supabase = get_supabase()
    try:
        query = supabase.table("RFQ-Tracker") \
            .select("*, Part_details(*)")
        
        if user.role != "admin":
            query = query.eq("created_by", user.id)
        
        res = query.eq("id", rfq_id).maybe_single().execute()
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": "Not found"}), 404

@api.route('/delete-rfq/<int:rfq_id>', methods=['DELETE'])
@login_required
def delete_rfq(user, rfq_id):
    supabase = get_supabase()
    try:
        query = supabase.table("RFQ-Tracker")
        if user.role != "admin":
            query = query.eq("created_by", user.id)
        
        # First check if RFQ exists and user has access
        check_res = query.select("id").eq("id", rfq_id).execute()
        if not check_res.data:
            return jsonify({"error": "Not found or access denied"}), 404
        
        supabase.table("Part_details").delete().eq("rfq_id", rfq_id).execute()
        supabase.table("RFQ-Tracker").delete().eq("id", rfq_id).execute()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/signup', methods=['POST'])
def signup(user):
    data = request.get_json()
    supabase = get_supabase()
    try:
        # Create user in Supabase Auth
        auth_res = supabase.auth.admin.create_user({
            "email": data['email'],
            "password": data['password'],
            "email_confirm": True
        })
        
        if auth_res.user:
            # Create profile
            profile_data = {
                "user_id": auth_res.user.id,
                "first_name": data.get('first_name', ''),
                "last_name": data.get('last_name', ''),
                "role": data.get('role', 'user')
            }
            supabase.table("profiles").insert(profile_data).execute()
            
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    supabase = get_supabase()
    try:
        auth_res = supabase.auth.sign_in_with_password({
            "email": data['email'],
            "password": data['password']
        })
        
        if auth_res.user and auth_res.session:
            response = jsonify({"success": True})
            response.set_cookie('access_token', auth_res.session.access_token, httponly=True, secure=False, samesite='Lax')
            response.set_cookie('csrf_token', auth_res.session.access_token[:10], httponly=False, secure=False, samesite='Lax')
            return response, 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/list-users', methods=['GET'])
def list_users(user):
    supabase = get_supabase()
    try:
        res = supabase.table("profiles").select("*").execute()
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/update-user/<user_id>', methods=['PUT'])
def update_user(user, user_id):
    data = request.get_json()
    supabase = get_supabase()
    try:
        update_data = {}
        if 'first_name' in data:
            update_data['first_name'] = data['first_name']
        if 'last_name' in data:
            update_data['last_name'] = data['last_name']
        if 'role' in data:
            update_data['role'] = data['role']
        
        supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/delete-user/<user_id>', methods=['DELETE'])
def delete_user(user, user_id):
    supabase = get_supabase()
    try:
        # Delete profile
        supabase.table("profiles").delete().eq("user_id", user_id).execute()
        # Note: Deleting from auth might require admin API, assuming profiles delete is enough
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
