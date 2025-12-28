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
        res = supabase.table("RFQ-Tracker") \
            .select('*, Part_details(*)') \
            .eq("created_by", user.id) \
            .order("created_at", desc=True) \
            .execute()
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/get-rfq/<int:rfq_id>', methods=['GET'])
@login_required
def get_rfq(user, rfq_id):
    supabase = get_supabase()
    try:
        res = supabase.table("RFQ-Tracker") \
            .select("*, Part_details(*)") \
            .eq("id", rfq_id) \
            .eq("created_by", user.id) \
            .single() \
            .execute()
        return jsonify({"success": True, "data": res.data}), 200
    except Exception as e:
        return jsonify({"error": "Not found"}), 404

@api.route('/delete-rfq/<int:rfq_id>', methods=['DELETE'])
@login_required
def delete_rfq(user, rfq_id):
    supabase = get_supabase()
    try:
        supabase.table("Part_details").delete().eq("rfq_id", rfq_id).execute()
        supabase.table("RFQ-Tracker").delete().eq("id", rfq_id).eq("created_by", user.id).execute()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500