from flask import Blueprint, request, jsonify
from src.auth.utils import login_required
from src.SupaClient import get_supabase, get_supabase_admin
import requests
from src.config import Config
import traceback

api = Blueprint('api', __name__, url_prefix='/api')

def get_user_info(user):
    role = getattr(user, 'role', user.get('role') if isinstance(user, dict) else 'user')
    u_id = getattr(user, 'id', user.get('id') if isinstance(user, dict) else None)
    return role, u_id

# --- RFQ ROUTES ---

@api.route('/make-rfq-entry', methods=['POST'])
@login_required
def make_entry(user):
    supabase = get_supabase()
    data = request.get_json()
    existing_rfq_id = data.get('id') 
    role, u_id = get_user_info(user)

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
            "created_by": u_id
        }
        
        if existing_rfq_id:
            supabase.table("RFQ-Tracker").update(header_data).eq("id", existing_rfq_id).execute()
            supabase.table("Part_details").delete().eq("rfq_id", existing_rfq_id).execute()
            new_rfq_id = existing_rfq_id
        else:
            header_res = supabase.table("RFQ-Tracker").insert(header_data).execute()
            new_rfq_id = header_res.data[0]['id']

        items = data.get('items', [])
        if items:
            items_to_insert = [{
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
            } for item in items]
            
            supabase.table("Part_details").insert(items_to_insert).execute()

        return jsonify({"success": True, "rfq_id": new_rfq_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/list-rfq-entry', methods=['GET'])
@login_required
def list_entry(user):
    supabase = get_supabase()
    role, u_id = get_user_info(user)
    try:
        # Everyone sees all rows for visibility
        res = supabase.table("RFQ-Tracker").select('*, Part_details(*)').order("created_at", desc=True).execute()
        processed_data = res.data
        
        # Mask sensitive info for Sales/Users
        if role != "admin":
            sensitive_fields = ["Unit$", "Unit₹", "Margin", "BCD", "Freight", "Insurance", "Clearance"]
            for rfq in processed_data:
                for part in rfq.get('Part_details', []):
                    for field in sensitive_fields:
                        if field in part:
                            part[field] = "---"

        return jsonify({"success": True, "data": processed_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/get-rfq/<int:rfq_id>', methods=['GET'])
@login_required
def get_rfq(user, rfq_id):
    supabase = get_supabase()
    role, u_id = get_user_info(user)
    try:
        # Get single RFQ with part details
        res = supabase.table("RFQ-Tracker").select('*, Part_details(*)').eq("id", rfq_id).execute()
        
        if not res.data or len(res.data) == 0:
            return jsonify({"error": "RFQ not found"}), 404
        
        rfq_data = res.data[0]
        
        # Mask sensitive info for Sales/Users
        if role != "admin":
            sensitive_fields = ["Unit$", "Unit₹", "Margin", "BCD", "Freight", "Insurance", "Clearance"]
            for part in rfq_data.get('Part_details', []):
                for field in sensitive_fields:
                    if field in part:
                        part[field] = "---"
        
        return jsonify({"success": True, "data": rfq_data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/delete-rfq/<int:rfq_id>', methods=['DELETE'])
@login_required
def delete_rfq(user, rfq_id):
    supabase = get_supabase()
    role, u_id = get_user_info(user)
    try:
        # Check permission: Only admin can delete anything. 
        # (Or add 'if role != "admin" and rfq.created_by != u_id' for ownership check)
        if role != "admin":
            return jsonify({"error": "Forbidden: Only admins can delete"}), 403
        
        supabase.table("Part_details").delete().eq("rfq_id", rfq_id).execute()
        supabase.table("RFQ-Tracker").delete().eq("id", rfq_id).execute()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- AUTH ROUTES ---

@api.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role = data.get('role', 'user')

    supabase_admin = get_supabase_admin() # Use admin client for user creation
    try:
        u_id = None
        user_exists = False
        
        # 1. Try to create user in Supabase Auth using admin API
        try:
            # Use admin API to create user (bypasses email confirmation)
            auth_res = supabase_admin.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            if auth_res and auth_res.user:
                u_id = auth_res.user.id
            else:
                return jsonify({"error": "Failed to create user: No user returned from auth"}), 500
        except Exception as auth_error:
            error_str = str(auth_error)
            print(f"Auth create_user error: {error_str}")
            
            # Check if user already exists
            if "already registered" in error_str.lower() or "already exists" in error_str.lower() or "User already registered" in error_str or "email address is already registered" in error_str.lower():
                # User exists - try to sign in to get user ID, or check profile table
                try:
                    # Try to sign in to verify user exists and get ID
                    signin_res = supabase_admin.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    if signin_res and signin_res.user:
                        u_id = signin_res.user.id
                        user_exists = True
                    else:
                        # If sign in fails, check profiles table for existing user_id by email
                        # Note: This requires email in profiles or we need to query auth differently
                        return jsonify({"error": "User with this email already exists. Please use a different email or reset password."}), 409
                except Exception as signin_error:
                    signin_err_str = str(signin_error)
                    print(f"Sign in error: {signin_err_str}")
                    # Check if we can find user via profiles (if email stored there)
                    # Otherwise, we'll need to handle this differently
                    return jsonify({"error": "User with this email already exists. Please use a different email."}), 409
            else:
                # Some other error - try regular signup as fallback
                try:
                    print("Trying regular signup as fallback...")
                    auth_res = supabase_admin.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    if auth_res and auth_res.user:
                        u_id = auth_res.user.id
                    else:
                        return jsonify({"error": f"Failed to create user: {error_str}"}), 500
                except Exception as signup_error:
                    signup_err_str = str(signup_error)
                    print(f"Regular signup also failed: {signup_err_str}")
                    return jsonify({"error": f"Failed to create user: {signup_err_str}"}), 500
        
        if not u_id:
            return jsonify({"error": "Failed to get user ID after creation"}), 500

        # 3. Check if profile already exists
        existing_profile = None
        try:
            profile_res = supabase_admin.table("profiles").select("*").eq("user_id", u_id).execute()
            if profile_res.data and len(profile_res.data) > 0:
                existing_profile = profile_res.data[0]
        except:
            pass  # If check fails, proceed with insert/update

        # 4. Create or update profile
        profile_data = {
            "first_name": first_name,
            "last_name": last_name,
            "role": role
        }
        
        role_set = False
        try:
            if existing_profile:
                # Update existing profile - try with role first
                try:
                    supabase_admin.table("profiles").update(profile_data).eq("user_id", u_id).execute()
                    role_set = True
                    message = "User profile updated successfully"
                except Exception as update_error:
                    error_str = str(update_error)
                    print(f"Profile update with role failed: {error_str}")
                    # Try without role first
                    profile_data_no_role = {
                        "first_name": first_name,
                        "last_name": last_name
                    }
                    supabase_admin.table("profiles").update(profile_data_no_role).eq("user_id", u_id).execute()
                    # Then try to set role separately using RPC function
                    try:
                        # Try using RPC function first (if it exists)
                        try:
                            print(f"Attempting to call RPC update_user_role with user_id={u_id}, role={role}")
                            rpc_result = supabase_admin.rpc("update_user_role", {
                                "p_user_id": str(u_id),
                                "p_new_role": str(role)
                            }).execute()
                            print(f"RPC call successful: {rpc_result}")
                            # Verify the role was actually set
                            verify_res = supabase_admin.table("profiles").select("role").eq("user_id", u_id).execute()
                            if verify_res.data and verify_res.data[0].get("role") == role:
                                print(f"Role verified successfully: {verify_res.data[0].get('role')}")
                                role_set = True
                                message = "User profile updated successfully"
                            else:
                                print(f"Warning: Role verification failed. Expected: {role}, Got: {verify_res.data[0].get('role') if verify_res.data else 'No data'}")
                                role_set = False
                                message = "User profile updated, but role verification failed. Please check manually."
                        except Exception as rpc_error:
                            rpc_error_str = str(rpc_error)
                            print(f"RPC function call failed: {rpc_error_str}")
                            # Check if function doesn't exist
                            if "Could not find the function" in rpc_error_str or "PGRST202" in rpc_error_str:
                                print("RPC function not found - it may not have been created correctly")
                                message = "User profile updated, but role could not be set. The database function may not exist. Please verify the SQL script was run correctly in Supabase."
                            else:
                                # If RPC fails for other reasons, try direct update as last resort
                                try:
                                    print("Trying direct update as fallback...")
                                    supabase_admin.table("profiles").update({"role": role}).eq("user_id", u_id).execute()
                                    role_set = True
                                    message = "User profile updated successfully"
                                except Exception as direct_error:
                                    direct_error_str = str(direct_error)
                                    print(f"Direct update also failed: {direct_error_str}")
                                    if "Only administrators" in direct_error_str or "P0001" in direct_error_str:
                                        message = "User profile updated, but role could not be set due to database trigger. The RPC function may not be working. Please check Supabase logs or update the role manually in admin panel."
                                    else:
                                        message = f"User profile updated, but role could not be set: {direct_error_str}"
                    except Exception as role_error:
                        error_str_role = str(role_error)
                        print(f"Role update failed: {error_str_role}")
                        if "Only administrators" in error_str_role or "P0001" in error_str_role:
                            message = "User profile updated, but role could not be set due to database trigger. Please verify the SQL function was created correctly in Supabase."
                        else:
                            message = f"User profile updated, but role could not be set: {error_str_role}"
            else:
                # Insert new profile - try with role first
                try:
                    profile_data["user_id"] = u_id
                    supabase_admin.table("profiles").insert(profile_data).execute()
                    role_set = True
                    message = "User created successfully"
                except Exception as insert_error:
                    error_str = str(insert_error)
                    print(f"Profile insert with role failed: {error_str}")
                    # Try without role first
                    profile_data_no_role = {
                        "user_id": u_id,
                        "first_name": first_name,
                        "last_name": last_name
                    }
                    supabase_admin.table("profiles").insert(profile_data_no_role).execute()
                    # Then try to set role separately using RPC function
                    try:
                        # Try using RPC function first (if it exists)
                        try:
                            print(f"Attempting to call RPC update_user_role with user_id={u_id}, role={role}")
                            rpc_result = supabase_admin.rpc("update_user_role", {
                                "p_user_id": str(u_id),
                                "p_new_role": str(role)
                            }).execute()
                            print(f"RPC call successful: {rpc_result}")
                            # Verify the role was actually set
                            verify_res = supabase_admin.table("profiles").select("role").eq("user_id", u_id).execute()
                            if verify_res.data and verify_res.data[0].get("role") == role:
                                print(f"Role verified successfully: {verify_res.data[0].get('role')}")
                                role_set = True
                                message = "User created successfully"
                            else:
                                print(f"Warning: Role verification failed. Expected: {role}, Got: {verify_res.data[0].get('role') if verify_res.data else 'No data'}")
                                role_set = False
                                message = "User created, but role verification failed. Please check manually."
                        except Exception as rpc_error:
                            rpc_error_str = str(rpc_error)
                            print(f"RPC function call failed: {rpc_error_str}")
                            # Check if function doesn't exist
                            if "Could not find the function" in rpc_error_str or "PGRST202" in rpc_error_str:
                                print("RPC function not found - it may not have been created correctly")
                                message = "User created, but role could not be set. The database function may not exist. Please verify the SQL script was run correctly in Supabase."
                            else:
                                # If RPC fails for other reasons, try direct update as last resort
                                try:
                                    print("Trying direct update as fallback...")
                                    supabase_admin.table("profiles").update({"role": role}).eq("user_id", u_id).execute()
                                    role_set = True
                                    message = "User created successfully"
                                except Exception as direct_error:
                                    direct_error_str = str(direct_error)
                                    print(f"Direct update also failed: {direct_error_str}")
                                    if "Only administrators" in direct_error_str or "P0001" in direct_error_str:
                                        message = "User created, but role could not be set due to database trigger. The RPC function may not be working. Please check Supabase logs or update the role manually in admin panel."
                                    else:
                                        message = f"User created, but role could not be set: {direct_error_str}"
                    except Exception as role_error:
                        error_str_role = str(role_error)
                        print(f"Role update failed: {error_str_role}")
                        if "Only administrators" in error_str_role or "P0001" in error_str_role:
                            message = "User created, but role could not be set due to database trigger. Please verify the SQL function was created correctly in Supabase."
                        else:
                            message = f"User created, but role could not be set: {error_str_role}"
        except Exception as profile_error:
            error_str = str(profile_error)
            print(f"Profile operation error: {error_str}")
            # Don't raise - return error message instead
            return jsonify({"error": f"Failed to create/update profile: {error_str}"}), 500
        
        return jsonify({"message": message, "user": u_id, "user_existed": user_exists}), 200

    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"Signup Error: {error_msg}")
        print(f"Full Traceback:\n{error_trace}")
        
        # Friendly error handling
        if "Only administrators" in error_msg or "P0001" in error_msg:
            return jsonify({"error": "Database Policy Error: Your API key does not have permission to set Roles. Please set SUPABASE_SERVICE_ROLE_KEY in your .env file."}), 403
        
        if "duplicate key" in error_msg.lower():
            return jsonify({"error": "This user already has a profile entry. The profile should have been updated instead."}), 409
            
        return jsonify({"error": error_msg}), 500

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
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/list-users', methods=['GET'])
@login_required
def list_users(user):
    role, u_id = get_user_info(user)
    if role != "admin":
        return jsonify({"error": "Forbidden: Only admins can list users"}), 403
    
    supabase = get_supabase_admin()
    try:
        res = supabase.table("profiles").select("*").execute()
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@api.route('/update-user/<user_id>', methods=['PUT'])
@login_required
def update_user(user, user_id):
    role, u_id = get_user_info(user)
    if role != "admin":
        return jsonify({"error": "Forbidden: Only admins can update users"}), 403
    
    data = request.get_json()
    supabase = get_supabase_admin()
    try:
        # Prepare update data
        update_data = {}
        if data.get('first_name'):
            update_data['first_name'] = data.get('first_name')
        if data.get('last_name'):
            update_data['last_name'] = data.get('last_name')
        new_role = data.get('role')
        
        # Update name fields first (if provided)
        if update_data:
            try:
                supabase.table("profiles").update(update_data).eq("user_id", user_id).execute()
            except Exception as name_error:
                print(f"Error updating name fields: {name_error}")
                return jsonify({"error": f"Failed to update user name: {str(name_error)}"}), 500
        
        # Try to update role separately using multiple approaches
        if new_role:
            role_updated = False
            error_messages = []
            
            # Approach 1: Direct update
            try:
                supabase.table("profiles").update({"role": new_role}).eq("user_id", user_id).execute()
                role_updated = True
            except Exception as role_error1:
                error_str1 = str(role_error1)
                error_messages.append(f"Direct update failed: {error_str1}")
                print(f"Direct role update failed: {error_str1}")
                
                # Approach 2: Try using RPC function to bypass trigger
                try:
                    # Call the database function that bypasses the trigger
                    supabase.rpc("update_user_role", {
                        "p_user_id": user_id,
                        "p_new_role": new_role
                    }).execute()
                    role_updated = True
                    print(f"Successfully updated role using RPC function")
                except Exception as rpc_error:
                    error_str2 = str(rpc_error)
                    error_messages.append(f"RPC call failed: {error_str2}")
                    print(f"RPC role update failed: {error_str2}")
                    # If function doesn't exist, provide helpful message
                    if "Could not find the function" in error_str2 or "PGRST202" in error_str2:
                        print("NOTE: Database function 'update_user_role' not found.")
                        print("Please run the SQL script in database_functions.sql in your Supabase SQL Editor.")
                    
                    # Approach 3: Try updating all fields together
                    try:
                        combined_update = {**update_data, "role": new_role}
                        supabase.table("profiles").update(combined_update).eq("user_id", user_id).execute()
                        role_updated = True
                    except Exception as combined_error:
                        error_str3 = str(combined_error)
                        error_messages.append(f"Combined update failed: {error_str3}")
                        print(f"Combined role update failed: {error_str3}")
            
            if not role_updated:
                # If all approaches failed, return a helpful error
                error_msg = "Could not update role. This is likely due to a database trigger or policy. "
                error_msg += "Please ensure you have set SUPABASE_SERVICE_ROLE_KEY in your .env file. "
                error_msg += f"Errors encountered: {'; '.join(error_messages)}"
                return jsonify({"error": error_msg, "details": error_messages}), 500
        
        return jsonify({"success": True, "message": "User updated successfully"}), 200
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"Update user error: {error_msg}")
        print(f"Traceback: {error_trace}")
        return jsonify({"error": f"Failed to update user: {error_msg}"}), 500

@api.route('/delete-user/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user, user_id):
    role, u_id = get_user_info(user)
    if role != "admin":
        return jsonify({"error": "Forbidden: Only admins can delete users"}), 403
    
    supabase = get_supabase_admin()
    try:
        # Delete profile first
        supabase.table("profiles").delete().eq("user_id", user_id).execute()
        # Note: Deleting from auth might require admin API, assuming profiles delete is enough
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500