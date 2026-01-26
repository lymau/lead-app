import streamlit as st
import requests
import json

# Mengambil URL dari secrets (pastikan .streamlit/secrets.toml sudah ada)
try:
    APPS_SCRIPT_API_URL = st.secrets['api_url']
except Exception:
    # Fallback untuk development lokal jika secrets belum di-load
    APPS_SCRIPT_API_URL = "" 
    st.error("API URL not found in secrets.")

# ==============================================================================
# MASTER DATA FETCHING
# ==============================================================================

def get_master_presales(action: str):
    """
    Mengambil data master dari sheet 'OBSERVERS' via API Apps Script.
    (Di-rename dari get_master agar sesuai dengan panggilan di utils.py)
    """
    if not APPS_SCRIPT_API_URL: return []

    url = f"{APPS_SCRIPT_API_URL}?action={action}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        json_data = response.json()
        if json_data.get("status") == 200:
            return json_data.get("data", [])
        else:
            st.error(f"API Error fetching {action}: {json_data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        st.error(f"Network error fetching {action}: {e}")
        return []

# ==============================================================================
# TRANSACTIONAL FUNCTIONS (GET)
# ==============================================================================

def get_all_leads_presales():
    """
    Mengambil semua data leads.
    (Di-rename dari get_all_leads agar sesuai dengan utils.py)
    """
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}

    url = f"{APPS_SCRIPT_API_URL}?action=leads"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching leads: {e}")
        return {"status": 500, "message": str(e)}

def get_single_lead(search_params):
    """Mengambil satu lead berdasarkan parameter (misal UID)."""
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}

    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    url = f"{APPS_SCRIPT_API_URL}?action=lead&{query_string}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching single lead: {e}")
        return {"status": 500, "message": str(e)}

def get_lead_by_uid(uid):
    """Wrapper khusus untuk mencari by UID."""
    return get_single_lead({"uid": uid})

def get_opportunity_summary(opp_id):
    """
    Mengambil data summary opportunity (misal untuk update stage).
    Saat ini menggunakan get_single_lead sebagai proxy pencarian by Opportunity ID.
    """
    # Note: Di kode asli Apps Script Anda, parameter pencarian fleksibel.
    # Kita gunakan opportunity_id sebagai kunci pencarian.
    return get_single_lead({"opportunity_id": opp_id})

# ==============================================================================
# TRANSACTIONAL FUNCTIONS (POST/UPDATE)
# ==============================================================================

def add_multi_line_opportunity(parent_data, product_lines):
    """Mengirim data opportunity baru dengan banyak baris solusi."""
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}
    
    # Cleaning payload agar sesuai dengan Apps Script
    payload = {
        "parent_data": parent_data,
        "product_lines": product_lines
    }
    
    url = f"{APPS_SCRIPT_API_URL}?action=addMultiLineOpportunity"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error submitting opportunity: {e}")
        return {"status": 500, "message": str(e)}

def update_lead(lead_data):
    """Update data lead parsial (Cost, Notes, dll)."""
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}

    url = f"{APPS_SCRIPT_API_URL}?action=update"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(lead_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error updating lead: {e}")
        return {"status": 500, "message": str(e)}

def update_full_opportunity(update_payload):
    """Update data full (Edit Data Entry Tab)."""
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}

    url = f"{APPS_SCRIPT_API_URL}?action=updateFullOpportunity"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(update_payload), headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error full update: {e}")
        return {"status": 500, "message": str(e)}

def update_opportunity_stage_bulk_enhanced(opp_id, new_stage, notes, date_val, user, closing_reason=None):
    """
    Fungsi khusus untuk update stage secara bulk (Logic Mockup).
    KARENA di backend Apps Script asli Anda belum ada endpoint 'updateStageBulk',
    kita gunakan endpoint 'updateBySales' atau 'update' biasa sebagai proxy jika memungkinkan,
    atau kembalikan error jika belum diimplementasi di backend.
    
    Untuk sementara, kita mapping ke 'updateBySales' yang Anda miliki di backend script 
    (Action: updateBySales).
    """
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}
    
    payload = {
        "opportunity_id": opp_id,
        "stage": new_stage,
        "sales_notes": notes, # Mapping notes ke sales_notes
        "stage_updated_date": str(date_val),
        "user": user,
        "closing_reason": closing_reason
    }

    url = f"{APPS_SCRIPT_API_URL}?action=updateBySales" 
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"status": 500, "message": f"Backend Error: {e}"}

def send_email_notification(email_data):
    """
    Mengirim email. 
    (Di-rename dari send_notification_email agar sesuai utils.py)
    """
    if not APPS_SCRIPT_API_URL: return {"status": 500, "message": "API URL Missing"}

    url = f"{APPS_SCRIPT_API_URL}?action=sendEmail"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(email_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return {"status": 500, "message": str(e)}