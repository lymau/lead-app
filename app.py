import streamlit as st
import requests
import json
import pandas as pd
import numpy as np

APPS_SCRIPT_API_URL = st.secrets['api_url']

st.set_page_config(
    page_title="Presales App - SISINDOKOM",
    page_icon=":clipboard:",
    initial_sidebar_state="expanded"
)

# Inisialisasi session state untuk mengingat apakah notifikasi sudah ditutup
if 'update_dismissed_v1_5' not in st.session_state:  # <-- DIUBAH
    st.session_state.update_dismissed_v1_5 = False # <-- DIUBAH

# Tampilkan notifikasi hanya jika belum ditutup
if not st.session_state.update_dismissed_v1_5: # <-- DIUBAH
    with st.container(border=True):
        st.subheader("🚀 Update Terbaru Aplikasi! (v1.5)") # <-- DIUBAH
        st.markdown("""
        #### 📊 Tampilan Baru: Kanban View Menggantikan "View Opportunities"!
        
        Tab "View Opportunities" yang lama telah diganti dengan **Kanban View** baru yang lebih visual dan fungsional.
        
        * **Tampilan Visual Pipeline:** Lihat semua opportunity Anda dalam 3 kolom: **Open**, **Closed Won**, & **Closed Lost**.
        * **Fokus pada Biaya:** Setiap kartu di Kanban sekarang menampilkan **Total Cost** (Lump Sum) dari opportunity tersebut.
        * **Drill-Down Detail:** Klik tombol **"View Details"** pada kartu untuk melihat ringkasan info dan tabel rincian semua solusinya.
        
        ----
        
        *Peningkatan sebelumnya (v1.4):*
        * **📜 Activity Log:** Tab 'Activity Log' ditambahkan untuk melacak semua riwayat perubahan data.
        * **Fitur Keterbacaan Angka (v1.3):** Format Rupiah di bawah kolom Cost.
        """)
        
        # Buat tombol untuk menutup notifikasi
        if st.button("Dismiss", key="dismiss_update_v1_5"): # <-- DIUBAH
            st.session_state.update_dismissed_v1_5 = True # <-- DIUBAH
            st.rerun()
    st.markdown("---")
    
def format_number(number):
    """Mengubah angka menjadi string dengan pemisah titik."""
    try:
        num = int(number)
        return f"{num:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

# ==============================================================================
# GET ALL MASTER DATA
# ==============================================================================

@st.cache_data(ttl=900) # Data akan di-cache selama 15 menit (900 detik)
def get_master(action: str):
    """
    Mengambil semua data dari sheet 'OBSERVERS' dari API Apps Script.
    Data akan di-cache untuk menghindari panggilan API berulang.
    Args:
        action (str): Tindakan yang ingin dilakukan, misalnya 'getObservers'.
    Returns:
        list: Daftar objek (dict) yang merepresentasikan setiap baris data observers,
              atau list kosong jika terjadi error atau tidak ada data.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return []

    url = f"{APPS_SCRIPT_API_URL}?action={action}"
    try:
        response = requests.get(url)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        json_data = response.json()
        if json_data.get("status") == 200:
            return json_data.get("data", [])
        else:
            st.error(f"API Error fetching data: {json_data.get('message', 'Unknown error')}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching data: {e}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error fetching data: {e}")
        return []

@st.cache_data(ttl=1800) # Data akan di-cache selama 30 menit (1800 detik)
def get_pillars():
    df = pd.DataFrame(get_master('getPillars'))
    pillar = df['Pillar'].unique().tolist()
    return pillar
    
def get_solutions(pillar):
    df = pd.DataFrame(get_master('getPillars'))
    solutions = df[df['Pillar'] == pillar]['Solution'].unique().tolist()
    return solutions

def get_services(solution):
    df = pd.DataFrame(get_master('getPillars'))
    services = df[df['Solution'] == solution]['Service'].unique().tolist()
    return services

def get_channels(brand):
    df = pd.DataFrame(get_master('getBrands'))
    channels = df[df['Brand'] == brand]['Channel'].unique().tolist()
    return channels

def get_sales_groups():
    df = pd.DataFrame(get_master('getSalesGroups'))
    sales_groups = df['SalesGroup'].unique().tolist()
    return sales_groups

def get_sales_name_by_sales_group(sales_group):
    df = pd.DataFrame(get_master('getSalesGroups'))
    sales_name = df[df['SalesGroup'] == sales_group]['SalesName'].unique().tolist()
    return sales_name

def get_activity_log():
    """Mengambil semua data log aktivitas dari API Apps Script."""
    # Kita bisa gunakan ulang fungsi get_master karena polanya sama
    return get_master('getActivityLog')

def get_pam_mapping_dict():
    """Mengambil data mapping Inputter -> PAM dari sheet dan mengubahnya menjadi dictionary."""
    mapping_data = get_master('getPamMapping')
    if not mapping_data:
        st.warning("Could not load Presales Account Manager mapping. Using default.")
        return {}
    return {item['InputterName']: item['PamName'] for item in mapping_data if 'InputterName' in item and 'PamName' in item}

# ==============================================================================
# FUNGSI UNTUK BERINTERAKSI DENGAN API
# ==============================================================================

def add_lead(lead_data):
    """
    Mengirimkan data lead baru ke endpoint 'add' API Apps Script.

    Args:
        lead_data (dict): Kamus berisi data lead baru (misal: {'name': 'John Doe', 'email': 'john@example.com'}).
                          'name' dan 'email' wajib ada.

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    url = f"{APPS_SCRIPT_API_URL}?action=add"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(lead_data), headers=headers)
        response.raise_for_status()  # Memunculkan HTTPError untuk status kode 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat menambahkan lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}


def update_lead(lead_data):
    """
    Mengirimkan data lead yang diperbarui ke endpoint 'update' API Apps Script.

    Args:
        lead_data (dict): Kamus berisi data lead yang akan diperbarui.
                          Wajib menyertakan 'id' dari lead yang akan diubah.

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    url = f"{APPS_SCRIPT_API_URL}?action=update"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(lead_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat memperbarui lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}

def update_full_opportunity(lead_data):
    """Mengirimkan data lengkap untuk diperbarui melalui API."""
    url = f"{APPS_SCRIPT_API_URL}?action=updateFullOpportunity"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(lead_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat memperbarui data: {e}")
        return None

def clean_data_for_display(data):
    """Membersihkan, mengatur ulang, dan MEMFORMAT KOLOM untuk ditampilkan."""
    
    # --- START PERBAIKAN ---
    # Cek dulu apakah inputnya sudah DataFrame (dari Kanban Detail)
    if isinstance(data, pd.DataFrame):
        if data.empty:
            return pd.DataFrame()
        df = data # Langsung gunakan, tidak perlu konversi
    
    # Cek apakah inputnya list kosong (dari API call biasa)
    elif not data: # Ini aman untuk list
        return pd.DataFrame()
    
    # Jika inputnya adalah list (dari API call), konversi ke DataFrame
    else:
        df = pd.DataFrame(data)
    # --- AKHIR PERBAIKAN ---

    desired_order = [
        'uid', 'presales_name', 'responsible_name','salesgroup_id','sales_name', 'company_name', 'opportunity_name', 'start_date', 'pillar', 'solution', 'service', 'brand', 'channel', 'distributor_name', 'cost', 'stage', 'notes', 'created_at', 'updated_at']
    
    existing_columns_in_order = [col for col in desired_order if col in df.columns]
    
    # Hindari error jika DataFrame kosong setelah difilter
    if not existing_columns_in_order:
        return pd.DataFrame()
        
    df = df[existing_columns_in_order]

    # 1. Format Kolom Angka (Cost, Selling Price)
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            # Konversi ke numerik, lalu format sebagai string "Rp ..."
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = df[col].apply(lambda x: f"Rp {format_number(x)}")

    # 2. Format Kolom Tanggal (start_date, created_at, updated_at)
    for date_col in ['start_date', 'created_at', 'updated_at']:
        if date_col in df.columns:
            
            if date_col == 'start_date':
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df[date_col] = df[date_col].dt.strftime('%d-%m-%Y')
            
            else:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce', utc=True)
                df[date_col] = df[date_col].dt.tz_convert('Asia/Jakarta')
                df[date_col] = df[date_col].dt.strftime('%d-%m-%Y %H:%M') 
            
            df[date_col] = df[date_col].replace('NaT', '', regex=False).replace('NaT NaT', '')

    return df

def get_all_leads():
    """
    Mengambil semua data leads dari endpoint 'leads' API Apps Script.

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    url = f"{APPS_SCRIPT_API_URL}?action=leads"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat mengambil semua leads: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}

def get_single_lead(search_params):
    """
    Mengambil data lead tertentu dari endpoint 'lead' API Apps Script
    berdasarkan parameter pencarian.

    Args:
        search_params (dict): Kamus berisi parameter pencarian (misal: {'id': 'abc'} atau {'email': 'test@example.com'}).

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    query_string = "&".join([f"{key}={value}" for key, value in search_params.items()])
    url = f"{APPS_SCRIPT_API_URL}?action=lead&{query_string}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat mengambil lead: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}
    
def add_multi_line_opportunity(payload):
    """Mengirimkan data opportunity dengan beberapa product line."""
    url = f"{APPS_SCRIPT_API_URL}?action=addMultiLineOpportunity"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.error(f"Error saat menambahkan opportunity: {e}")
        return None

def send_notification_email(email_data):
    """
    Mengirimkan notifikasi email melalui API Apps Script.

    Args:
        email_data (dict): Kamus berisi data email (misal: {'recipients': ['a@b.com'], 'subject': 'sub', 'body': 'bod'}).
                           'recipients', 'subject', dan 'body' wajib ada.

    Returns:
        dict: Respon JSON dari API.
    """
    if APPS_SCRIPT_API_URL == "GANTI_DENGAN_URL_WEB_APP_ANDA_DI_SINI":
        st.error("Harap perbarui APPS_SCRIPT_API_URL dengan URL Web App Anda!")
        return {"status": 500, "message": "Konfigurasi URL API belum lengkap."}

    url = f"{APPS_SCRIPT_API_URL}?action=sendEmail"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(email_data), headers=headers)
        response.raise_for_status()  # Memunculkan HTTPError untuk status kode 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error saat mengirim notifikasi: {e}")
        return {"status": 500, "message": f"Request Error: {e}"}
    except json.JSONDecodeError as e:
        st.error(f"Error parsing response JSON: {e}")
        return {"status": 500, "message": f"JSON Decode Error: {e}"}

# ==============================================================================
# ANTARMUKA STREAMLIT
# ==============================================================================

st.title("Presales App - SISINDOKOM")
st.markdown("---")

# Tab navigasi
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Add Opportunity", "View Opportunities", "Search Opportunity", "Update Opportunity", "Edit Opportunity", "Activity Log"])

# Inisialisasi session state
if 'product_lines' not in st.session_state: st.session_state.product_lines = [{"id": 0}]
if 'submission_message' not in st.session_state: st.session_state.submission_message = None
if 'new_uids' not in st.session_state: st.session_state.new_uids = None
if 'edit_submission_message' not in st.session_state: st.session_state.edit_submission_message = None
if 'edit_new_uid' not in st.session_state: st.session_state.edit_new_uid = None

# Tambahan untuk Kanban View (Tab 2)
if 'selected_kanban_opp_id' not in st.session_state: st.session_state.selected_kanban_opp_id = None
if 'kanban_form_message' not in st.session_state: st.session_state.kanban_form_message = None

with tab1:
    st.header("Add New Opportunity (Multi-Solution)")
    st.info("Fill out the main details once, then add one or more solutions below.")
    
    inputter_to_pam_map = get_pam_mapping_dict()
    DEFAULT_PAM = "Not Assigned"

    # --- BAGIAN 1: DATA INDUK (PARENT DATA) ---
    st.subheader("Step 1: Main Opportunity Details")
    
    parent_col1, parent_col2 = st.columns(2)
    with parent_col1:
        # KOREKSI: Implementasi penuh logika PAM otomatis/fleksibel
        presales_name_obj = st.selectbox("Inputter", get_master('getPresales'), format_func=lambda x: x.get("PresalesName", "Unknown"), key="parent_presales_name")
        selected_inputter_name = presales_name_obj.get("PresalesName", "") if presales_name_obj else ""
        
        pam_rule = inputter_to_pam_map.get(selected_inputter_name, DEFAULT_PAM)
        
        if pam_rule == "FLEKSIBEL":
            pam_object = st.selectbox("Choose Presales Account Manager", get_master('getResponsibles'), format_func=lambda x: x.get("Responsible", "Unknown"), key="pam_flexible_choice")
            responsible_name_final = pam_object.get('Responsible', '') if pam_object else ""
        else:
            responsible_name_final = pam_rule
            st.text_input("Presales Account Manager", value=responsible_name_final, disabled=True)

        salesgroup_id = st.selectbox("Choose Sales Group", get_sales_groups(), key="parent_salesgroup_id")
        sales_name = st.selectbox("Choose Sales Name", get_sales_name_by_sales_group(st.session_state.get("parent_salesgroup_id")), key="parent_sales_name")


    with parent_col2:
        opportunity_name = st.selectbox("Opportunity Name", [opt.get("Desc") for opt in get_master('getOpportunities')], key="parent_opportunity_name", accept_new_options=True, index=None, placeholder="Choose or type new opportunity name")
        st.warning("""
        Format Opportunity Name:
                   
        - If direct:
        End User - Opportunity Name - Month Year
                    
        - If via B2B Channel:
        [B2B Channel] End User - Opportunity Name - Month Year
                    
                    """)
        
        start_date = st.date_input("Start Date", key="parent_start_date")
        all_companies_data = get_master('getCompanies')
        companies_df = pd.DataFrame(all_companies_data)
        
        is_company_listed = st.radio("Is the company listed?", ("Yes", "No"), key="parent_is_company_listed", horizontal=True)

        company_name_final = ""
        vertical_industry_final = ""

        if is_company_listed == "Yes":
            company_name_obj = st.selectbox(
                "Choose Company",
                all_companies_data,
                format_func=lambda x: x.get("Company", "Pilih Perusahaan"),
                key="parent_company_select"
            )
            if company_name_obj:
                company_name_final = company_name_obj.get("Company", "")
                # Mencari vertical industry berdasarkan company yang dipilih
                if not companies_df.empty and 'Company' in companies_df.columns and 'Vertical Industry' in companies_df.columns:
                    filtered_industry = companies_df[companies_df['Company'] == company_name_final]['Vertical Industry']
                    if not filtered_industry.empty:
                        vertical_industry_final = filtered_industry.iloc[0]
            st.text_input("Vertical Industry", value=vertical_industry_final, disabled=True, key="parent_vertical_industry_disabled")
        
        else: # Jika pilihan "No"
            company_name_final = st.text_input("Company Name (if not listed)", key="parent_company_text_input")
            
            vertical_industry_options = []
            if not companies_df.empty and 'Vertical Industry' in companies_df.columns:
                vertical_industry_options = sorted(companies_df['Vertical Industry'].unique().tolist())
            
            vertical_industry_final = st.selectbox(
                "Choose Vertical Industry",
                vertical_industry_options,
                key="parent_vertical_industry_select"
            )

    # --- BAGIAN 2: PRODUCT LINES DINAMIS ---
    st.markdown("---")
    st.subheader("Step 2: Add Solutions")
    for i, line in enumerate(st.session_state.product_lines):
        with st.container(border=True):
            cols = st.columns([0.9, 0.1])
            cols[0].markdown(f"**Solution {i+1}**")
            # Tombol hapus hanya muncul jika ada lebih dari 1 baris
            if len(st.session_state.product_lines) > 1:
                if cols[1].button("❌", key=f"remove_{line['id']}", help="Remove this line"):
                    st.session_state.product_lines.pop(i)
                    st.rerun()

            line_col1, line_col2 = st.columns(2)
            with line_col1:
                line['pillar'] = st.selectbox("Pillar", get_pillars(), key=f"pillar_{line['id']}")
                solution_options = get_solutions(line['pillar'])
                line['solution'] = st.selectbox("Solution", solution_options, key=f"solution_{line['id']}")
                service_options = get_services(line['solution'])
                line['service'] = st.selectbox("Service", service_options, key=f"service_{line['id']}")
            
            with line_col2:
                brand_options = [b.get("Brand") for b in get_master('getBrands')]
                line['brand'] = st.selectbox("Brand", brand_options, key=f"brand_{line['id']}")
                channel_options = get_channels(line.get('brand'))
                line['channel'] = st.selectbox("Channel", channel_options, key=f"channel_{line['id']}")
                line['cost'] = st.number_input("Cost", min_value=0, step=1000, key=f"cost_{line['id']}", format="%d")

                # Tambahkan st.caption di bawahnya untuk memberikan umpan balik
                st.caption(f"Reads: Rp {format_number(line.get('cost', 0))}")
                note_message = "Note: All values must be in Indonesian Rupiah (IDR). (e.g., 1 USD = 16,500 IDR)."
                if line.get("brand") == "Cisco":
                    note_message += " For Cisco only: First, apply a 50% discount to the price, then multiply by the IDR exchange rate."
                st.info(note_message)
                is_via = st.radio("Via Distributor?", ("Yes", "No"), index=1, key=f"is_via_{line['id']}", horizontal=True)
                if is_via == "Yes":
                    dist_options = [d.get("Distributor") for d in get_master('getDistributors')]
                    line['distributor_name'] = st.selectbox("Distributor", dist_options, key=f"dist_{line['id']}")
                else:
                    line['distributor_name'] = "Not via distributor"
            
            # Kolom Notes sekarang ada di dalam setiap product line
            line['notes'] = st.text_area("Notes for this Solution", key=f"notes_{line['id']}", height=100)
            st.info("""
            * **If the brand is 'Others'**, please specify the brand name in the notes.
            * **If a distributor is not listed**, please inform the admin to have it added.
            * **For any other remarks**, please use this notes field.
            """)
    # Pastikan ada setidaknya satu product line
    # Tombol untuk menambah baris baru
    if st.button("➕ Add Another Solution"):
        # Buat ID unik baru untuk key widget
        new_id = max(line['id'] for line in st.session_state.product_lines) + 1 if st.session_state.product_lines else 0
        st.session_state.product_lines.append({
            "id": new_id
        })
        st.rerun()

    # --- BAGIAN 3: SUBMIT ---
    st.markdown("---")
    st.subheader("Step 3: Submit Opportunity")

    # 1. Inisialisasi variabel di luar blok if
    all_presales_data = get_master('getPresales')
    presales_options = []
    presales_name_to_email_map = {}
    list_of_emails = []

    # 2. Coba proses data presales jika berhasil dimuat
    if all_presales_data:
        try:
            presales_name_to_email_map = {
                item.get("PresalesName"): item.get("Email") 
                for item in all_presales_data if item.get("PresalesName") and item.get("Email")
            }
            presales_options = sorted(list(presales_name_to_email_map.keys())) # Urutkan nama agar mudah dicari
        except Exception as e:
            # Jika ada error saat memproses data, tampilkan peringatan
            st.warning(f"Error processing Presales data: {e}")
    else:
        # Jika data tidak berhasil dimuat sama sekali
        st.warning("Unable to load Presales list. Email notification feature will not be available.")

    # 3. Tampilkan st.multiselect. Ini akan selalu muncul.
    # Jika presales_options kosong, widget akan muncul tapi tidak ada pilihan.
    selected_presales_names = st.multiselect(
        "Tag Presales for Push Notification (Optional)",
        options=presales_options,
        help="Select one or more Presales names to notify via email upon submission. If none selected, no email will be sent.",
    )

    # 4. Proses email hanya jika ada nama yang dipilih
    if selected_presales_names:
        list_of_emails = [presales_name_to_email_map.get(name) for name in selected_presales_names if presales_name_to_email_map.get(name)]


    # 5. Tombol submit dan logikanya (tidak ada perubahan di sini)
    if st.button("Submit Opportunity and All Solutions", type="primary"):
        # Kumpulkan data induk
        parent_payload = {
            "presales_name": selected_inputter_name,
            "responsible_name": responsible_name_final,
            "salesgroup_id": salesgroup_id,
            "sales_name": sales_name,
            "opportunity_name": opportunity_name,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "company_name": company_name_final,
            "vertical_industry": vertical_industry_final
        }

        # Kumpulkan data product lines
        lines_payload = [line.copy() for line in st.session_state.product_lines]
        
        final_payload = {"parent_data": parent_payload, "product_lines": lines_payload}
        
        with st.spinner("Submitting all solutions..."):
            response = add_multi_line_opportunity(final_payload)
            if response and response.get("status") == 200:
                st.session_state.submission_message = response.get("message")
                created_data = response.get('data', [])
                st.session_state.new_uids = [data.get('uid') for data in created_data]
                
                list_of_emails = [presales_name_to_email_map.get(name) for name in selected_presales_names if presales_name_to_email_map.get(name)]
                if list_of_emails:
                    opp_id = created_data[0].get('opportunity_id', 'N/A') if created_data else 'N/A'
                    email_subject = f"New Multi-Solution Opportunity Added: {parent_payload['opportunity_name']}"
                    email_body = f"A new opportunity '{parent_payload['opportunity_name']}' (ID: {opp_id}) has been added by {selected_inputter_name} with {len(lines_payload)} solution(s). Please follow up."
                    send_notification_email({"recipients": list_of_emails, "subject": email_subject, "body": email_body})
                    st.session_state.submission_message += f" | Email notification sent to {len(list_of_emails)} recipient(s)."

                st.session_state.product_lines = [{"id": 0}]
                st.rerun()
            else:
                st.error(f"Failed to submit: {response.get('message', 'Unknown error') if response else 'No response from server'}")

    if st.session_state.submission_message:
        st.success(st.session_state.submission_message)
        if st.session_state.new_uids: st.info(f"UIDs for update: {st.session_state.new_uids}")
        st.session_state.submission_message = None
        st.session_state.new_uids = None


with tab2:
    st.header("Kanban View by Opportunity Stage")
    
    # 1. Ambil data 'leads' (detail)
    with st.spinner("Fetching all leads data for Kanban..."):
        all_leads_response = get_all_leads()
        
    if not all_leads_response or all_leads_response.get("status") != 200:
        st.error("Could not fetch leads data from API.")
    else:
        raw_all_leads_data = all_leads_response.get("data", [])

        if not raw_all_leads_data:
            st.info("No data found to display.")
        else:
            df_master = pd.DataFrame(raw_all_leads_data)

            # =============================================================
            # ▼▼▼ BLOK FILTER BARU ▼▼▼
            # =============================================================
            st.markdown("---")
            st.subheader("Filters")
            
            # Ambil opsi filter dari df_master
            inputter_options = sorted(df_master['presales_name'].dropna().unique().tolist())
            pam_options = sorted(df_master['responsible_name'].dropna().unique().tolist())
            group_options = sorted(df_master['salesgroup_id'].dropna().unique().tolist())

            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                selected_inputters = st.multiselect(
                    "Filter by Inputter", 
                    inputter_options, 
                    key="kanban_filter_inputter"
                )
            with f_col2:
                selected_pams = st.multiselect(
                    "Filter by Presales AM", 
                    pam_options, 
                    key="kanban_filter_pam"
                )
            with f_col3:
                selected_groups = st.multiselect(
                    "Filter by Sales Group", 
                    group_options, 
                    key="kanban_filter_group"
                )

            # Terapkan filter ke df_master
            df_filtered = df_master.copy()
            if selected_inputters:
                df_filtered = df_filtered[df_filtered['presales_name'].isin(selected_inputters)]
            if selected_pams:
                df_filtered = df_filtered[df_filtered['responsible_name'].isin(selected_pams)]
            if selected_groups:
                df_filtered = df_filtered[df_filtered['salesgroup_id'].isin(selected_groups)]
            
            st.markdown("---")
            # =============================================================
            # ▼▼▼ LOGIKA KANBAN (SEKARANG MENGGUNAKAN 'df_filtered') ▼▼▼
            # =============================================================
            
            # --- 1. LOGIKA NAVIGASI (DETAIL VIEW) --------------------
            if st.session_state.selected_kanban_opp_id:
                
                selected_id = st.session_state.selected_kanban_opp_id
                
                if st.button("⬅️ Back to Kanban View"):
                    st.session_state.selected_kanban_opp_id = None
                    if 'kanban_form_message' in st.session_state: del st.session_state.kanban_form_message
                    st.rerun()
                
                # Gunakan df_filtered untuk mengambil detail
                opportunity_details_df = df_filtered[df_filtered['opportunity_id'] == selected_id]
                
                if opportunity_details_df.empty:
                    st.error(f"Could not find solution details for {selected_id} (mungkin tersembunyi oleh filter).")
                else:
                    lead_data = opportunity_details_df.iloc[0].to_dict()
                    opp_name = lead_data.get('opportunity_name', 'N/A')
                    company_name = lead_data.get('company_name', 'N/A')
                    
                    st.header(f"Detail for: {opp_name}")
                    st.subheader(f"Client: {company_name}")
                    
                    st.markdown("---")
                    st.subheader("Opportunity Summary")
                    col1, col2 = st.columns(2)
                    
                    start_date_str = lead_data.get('start_date', 'N/A')
                    try:
                        start_date_obj = pd.to_datetime(start_date_str)
                        formatted_start_date = start_date_obj.strftime('%d-%m-%Y')
                    except Exception:
                        formatted_start_date = 'N/A' 

                    with col1:
                        st.markdown(f"👤 **Inputter:** {lead_data.get('presales_name', 'N/A')}")
                        st.markdown(f"🧑‍💼 **Presales Account Manager:** {lead_data.get('responsible_name', 'N/A')}")
                        st.markdown(f"🗓️ **Start Date:** {formatted_start_date}") 
                        st.markdown(f"🏷️ **Brand:** {lead_data.get('brand', 'N/A')}")
                    with col2:
                        st.markdown(f"🏢 **Company:** {lead_data.get('company_name', 'N/A')}")
                        st.markdown(f"🏭 **Vertical Industry:** {lead_data.get('vertical_industry', 'N/A')}") 
                        st.markdown(f"ℹ️ **Stage:** {lead_data.get('stage', 'N/A')}")
                        st.markdown(f"🆔 **Opportunity ID:** {lead_data.get('opportunity_id', 'N/A')}")
                    st.markdown("---")

                    st.subheader("Solution Details")
                    st.dataframe(clean_data_for_display(opportunity_details_df))

            # --- 2. TAMPILAN KANBAN (MAIN VIEW) ----------------------
            else:
                # Cek jika df_filtered kosong setelah filter diterapkan
                if df_filtered.empty:
                    st.warning("No data matches your filter.")
                else:
                    st.markdown("Displaying unique data per opportunity with total cost. Click 'View Details' on the card.")

                    # Pastikan kolom cost dan stage ada
                    if 'cost' not in df_filtered.columns:
                        df_filtered['cost'] = 0
                    df_filtered['cost'] = pd.to_numeric(df_filtered['cost'], errors='coerce').fillna(0)
                    
                    # Hitung total 'cost' dari data yang SUDAH DIFILTER
                    df_sums = df_filtered.groupby('opportunity_id')['cost'].sum().reset_index()
                    
                    # Ambil data unik dari data yang SUDAH DIFILTER
                    df_details = df_filtered.drop_duplicates(subset=['opportunity_id'], keep='first')
                    
                    if 'cost' in df_details.columns:
                        df_details = df_details.drop(columns=['cost'])
                    df_opps = pd.merge(df_details, df_sums, on='opportunity_id', how='left')

                    if 'stage' not in df_opps.columns:
                        df_opps['stage'] = 'Open'
                    
                    df_opps['stage'] = df_opps['stage'].fillna('Open')
                    open_opps = df_opps[df_opps['stage'] == 'Open']
                    won_opps = df_opps[df_opps['stage'] == 'Closed Won']
                    lost_opps = df_opps[df_opps['stage'] == 'Closed Lost']

                    col1, col2, col3 = st.columns(3)

                    def render_kanban_card(row):
                        with st.container(border=True):
                            st.markdown(f"**{row.get('opportunity_name', 'N/A')}**")
                            st.markdown(f"*{row.get('company_name', 'N/A')}*")
                            st.write(f"Inputter: {row.get('presales_name', 'N/A')}")
                            price = int(row.get('cost', 0) or 0)
                            st.markdown(f"**Total Cost: {price:,}**")
                            st.caption(f"ID: {row.get('opportunity_id', 'N/A')}")
                            
                            opp_id = row.get('opportunity_id')
                            if st.button(f"View Details", key=f"btn_detail_{opp_id}"):
                                st.session_state.selected_kanban_opp_id = opp_id
                                st.rerun()

                    with col1:
                        st.markdown(f"### 🧊 Open ({len(open_opps)})")
                        st.markdown("---")
                        for _, row in open_opps.iterrows():
                            render_kanban_card(row)

                    with col2:
                        st.markdown(f"### ✅ Closed Won ({len(won_opps)})")
                        st.markdown("---")
                        for _, row in won_opps.iterrows():
                            render_kanban_card(row)

                    with col3:
                        st.markdown(f"### ❌ Closed Lost ({len(lost_opps)})")
                        st.markdown("---")
                        for _, row in lost_opps.iterrows():
                            render_kanban_card(row)

with tab3:
    st.header("Search Opportunities")
    keywords = [
        "Inputter",
        "Presales Account Manager",
        "Opportunity Name",
        "Pillar",
        "Solution",
        "Service",
        "Brand",
        "Channel",
        "Company",
        "Distributor"
    ]
    search_by_option = st.selectbox("Search By", keywords, key="search_option")

    if search_by_option == "Inputter":
        presales_keywords = [x.get("PresalesName", "Unknown") for x in get_master('getPresales')]
        search_query = st.selectbox("Select Inputter", presales_keywords, key="search_query")
    elif search_by_option == "Presales Account Manager":
        responsible_keywords = [x.get("Responsible", "Unknown") for x in get_master('getResponsibles')]
        search_query = st.selectbox("Select Presales Account Manager", responsible_keywords, key="search_query")
    elif search_by_option == "Opportunity Name":
        opportunity_name_keywords = [x.get("Desc", "Unknown") for x in get_master('getOpportunities')]
        search_query = st.selectbox("Select Opportunity Name", opportunity_name_keywords, key="search_query")
    elif search_by_option == "Pillar":
        pillar_keywords = get_pillars()
        search_query = st.selectbox("Select Pillar", pillar_keywords, key="search_query")
    elif search_by_option == "Solution":
        pillar = st.selectbox("Select Pillar for Solution", get_pillars(), key="search_pillar")
        solution_keywords = get_solutions(pillar)
        search_query = st.selectbox("Select Solution", solution_keywords, key="search_query")
    elif search_by_option == "Service":
        pillar = st.selectbox("Select Pillar for Service", get_pillars(), key="search_pillar_service")
        solution = st.selectbox("Select Solution for Service", get_solutions(pillar), key="search_solution")
        service_keywords = get_services(solution)
        search_query = st.selectbox("Select Service", service_keywords, key="search_query")
    elif search_by_option == "Brand":
        brand_keywords = [x.get("Brand", "Unknown") for x in get_master('getBrands')]
        search_query = st.selectbox("Select Brand", brand_keywords, key="search_query")
    elif search_by_option == "Channel":
        channel_keywords = [x for x in pd.DataFrame(get_master('getBrands'))["Channel"].unique().tolist()]
        search_query = st.selectbox("Select Channel", channel_keywords, key="search_query")
    elif search_by_option == "Company":
        company_keywords = [x.get("Company", "Unknown") for x in get_master('getCompanies')]
        search_query = st.selectbox("Select Company", company_keywords, key="search_query")
    elif search_by_option == "Distributor":
        distributor_keywords = [x.get("Distributor", "Unknown") for x in get_master('getDistributors')]
        search_query = st.selectbox("Select Distributor", distributor_keywords, key="search_query")

    if st.button("Search Opportunity"):
        if search_query:
            search_params = {}
            if search_by_option == "Inputter":
                search_params["presales_name"] = search_query
            elif search_by_option == "Presales Account Manager":
                search_params["responsible_name"] = search_query
            elif search_by_option == "Opportunity Name":
                search_params["opportunity_name"] = search_query
            elif search_by_option == "Pillar":
                search_params["pillar"] = search_query
            elif search_by_option == "Solution":
                search_params["solution"] = search_query
            elif search_by_option == "Service":
                search_params["service"] = search_query
            elif search_by_option == "Brand":
                search_params["brand"] = search_query
            elif search_by_option == "Channel":
                search_params["channel"] = search_query
            elif search_by_option == "Company":
                search_params["company_name"] = search_query
            elif search_by_option == "Distributor":
                search_params["distributor_name"] = search_query
            else:
                st.error("Search option is not valid.")

            with st.spinner(f"Searching opportunity by {search_by_option}: {search_query}..."):
                response = get_single_lead(search_params)
                if response and response.get("status") == 200:
                    found_leads = response.get("data")
                    if found_leads:
                        st.success(f"Found {len(found_leads)} opportunity(s).")
                        cleaned_df = clean_data_for_display(found_leads)
                        st.dataframe(cleaned_df)
                    else:
                        st.info("No opportunity found with the given criteria.")
                else:
                    st.error(response.get("message", "Failed to search opportunity."))
                    st.json(response)
        else:
            st.warning("Please enter a search query.")

with tab4:
    st.header("Update Opportunity")

    # Inisialisasi semua session_state yang dibutuhkan di awal
    if 'lead_to_update' not in st.session_state:
        st.session_state.lead_to_update = None
    if 'update_message' not in st.session_state:
        st.session_state.update_message = None

    # BARU: Blok untuk menampilkan pesan dari session_state
    if st.session_state.update_message:
        # Tampilkan pesan sukses jika ada
        st.success(st.session_state.update_message)
        # Hapus pesan setelah ditampilkan
        st.session_state.update_message = None

    uid = st.text_input("Enter UID to search opportunity", key="uid_update")
    
    if st.button("Get Opportunity Data"):
        st.session_state.lead_to_update = None
        st.session_state.update_message = None # Hapus juga pesan lama saat cari baru
        if uid:
            with st.spinner(f"Retrieving opportunity data with uid: {uid}..."):
                response = get_single_lead({"uid": uid})
                if response and response.get("status") == 200 and response.get("data"):
                    st.session_state.lead_to_update = response.get("data")[0]
                else:
                    st.error(f"Failed to retrieve data or UID '{uid}' not found.")
        else:
            st.warning("Please enter a UID.")

    if st.session_state.lead_to_update:
        lead = st.session_state.lead_to_update
        
        st.write(f"🆔 **Data Lead dengan UID:** {lead.get('uid', 'N/A')}")
        st.write(f"👤 **Inputter:** {lead.get('presales_name', 'Unknown')}")
        st.write(f"🧑‍💼 **Presales Account Manager:** {lead.get('responsible_name', 'Unknown')}")
        st.write(f"🏷️ **Opportunity Name:** {lead.get('opportunity_name', 'Unknown')}")
        st.write(f"🏛️ **Pillar:** {lead.get('pillar', 'Unknown')}")
        st.write(f"🧩 **Solution:** {lead.get('solution', 'Unknown')}")
        st.write(f"🛠️ **Service:** {lead.get('service', 'Unknown')}")
        st.write(f"🏷️ **Brand:** {lead.get('brand', 'Unknown')}")
        st.write(f"📡 **Channel:** {lead.get('channel', 'Unknown')}")
        st.write(f"🏢 **Company:** {lead.get('company_name', 'Unknown')}")
        st.write(f"🏭 **Vertical Industry:** {lead.get('vertical_industry', 'Unknown')}")
        st.write(f"💰 **Cost:** {lead.get('cost', 0)}")
        st.write(f"📝 **Notes:** {lead.get('notes', 'No notes available')}")
        st.write(f"📅 **Created At:** {lead.get('created_at', 'Unknown')}")
        st.markdown("---")

        notes = st.text_area("Notes", value=lead.get("notes", ""), height=100, key="update_notes")
        try:
            # Menggunakan float dulu untuk menangani jika ada angka desimal dari sheet (misal: 10000.0)
            initial_cost_value = int(float(lead.get("cost", 0)))
        except (ValueError, TypeError):
            initial_cost_value = 0
        
        cost = st.number_input("Cost", value=initial_cost_value, min_value=0, step=10000, key="update_cost")
        st.caption(f"Reads: Rp {format_number(st.session_state.get('update_cost', 0))}")

        with st.form(key="update_lead_form_submit_only"):
            submit_button = st.form_submit_button("Update Opportunity")
            
            if submit_button:
                update_data = {
                    "uid": lead.get('uid'),
                    "notes": st.session_state.update_notes,
                    "cost": st.session_state.update_cost,
                    "user": lead.get('presales_name')
                }
                with st.spinner(f"Updating opportunity {uid}..."):
                    update_response = update_lead(update_data)
                    if update_response and update_response.get("status") == 200:
                        # BARU: SIMPAN pesan ke session_state, JANGAN langsung tampilkan
                        st.session_state.update_message = update_response.get("message")
                        st.session_state.lead_to_update = None
                        st.rerun()
                    else:
                        st.error(update_response.get("message", "Failed to update opportunity."))
                        
with tab5:
    st.header("Edit Data Entry (Error Correction)")
    st.warning("Use this page to correct input errors. Please be aware that changing the Sales Group will generate a new UID.")
    if 'lead_to_edit' not in st.session_state:
        st.session_state.lead_to_edit = None

    uid_to_find = st.text_input("Enter the UID of the opportunity to be corrected:", key="uid_finder_edit")
    if st.button("Find Data to Edit"):
        st.session_state.lead_to_edit = None
        if uid_to_find:
            with st.spinner("Fetching data..."):
                response = get_single_lead({"uid": uid_to_find})
                if response and response.get("status") == 200 and response.get("data"):
                    st.session_state.lead_to_edit = response.get("data")[0]
                    st.success("Data found. Please edit the form below.")
                else:
                    st.error("UID not found. Please double-check the UID and try again.")
        else:
            st.warning("Please enter a UID.")
    
    if st.session_state.edit_submission_message:
        st.success(st.session_state.edit_submission_message)
        if st.session_state.edit_new_uid:
            st.info(f"IMPORTANT: The UID has been updated. The new UID is: {st.session_state.edit_new_uid}")
        st.session_state.edit_submission_message = None
        st.session_state.edit_new_uid = None

    if st.session_state.lead_to_edit:
        lead = st.session_state.lead_to_edit
        st.markdown("---")
        st.subheader(f"Step 2: Edit Data for '{lead.get('opportunity_name', '')}'")

        def get_index(data_list, value, key=None):
            try:
                if key: return [item.get(key) for item in data_list].index(value)
                else: return data_list.index(value)
            except (ValueError, TypeError): return 0
        
        # --- PERUBAHAN DIMULAI DI SINI ---
        
        # Ambil semua data master yang dibutuhkan
        all_sales_groups = get_sales_groups()
        all_responsibles = get_master('getResponsibles')
        all_pillars = get_pillars()
        all_brands = get_master('getBrands')
        all_companies_data = get_master('getCompanies')
        companies_df = pd.DataFrame(all_companies_data)
        all_distributors = get_master('getDistributors')

        # Form Edit
        col1, col2 = st.columns(2)
        with col1:
            edited_sales_group = st.selectbox(
                "Sales Group", 
                all_sales_groups, 
                index=get_index(all_sales_groups, lead.get('salesgroup_id')), 
                key="edit_sales_group"
            )
            
            # Widget untuk mengubah Sales Name (opsi bergantung pada Sales Group)
            sales_name_options = get_sales_name_by_sales_group(st.session_state.edit_sales_group)
            edited_sales_name = st.selectbox(
                "Sales Name", 
                sales_name_options, 
                index=get_index(sales_name_options, lead.get('sales_name')), 
                key="edit_sales_name"
            )

            edited_responsible = st.selectbox("Presales Account Manager", all_responsibles, index=get_index(all_responsibles, lead.get('responsible_name'), 'Responsible'), format_func=lambda x: x.get("Responsible", ""), key="edit_responsible")
        
            edited_pillar = st.selectbox("Pillar", all_pillars, index=get_index(all_pillars, lead.get('pillar')), key="edit_pillar")
            solution_options = get_solutions(st.session_state.edit_pillar)
            edited_solution = st.selectbox("Solution", solution_options, index=get_index(solution_options, lead.get('solution')), key="edit_solution")

        with col2:
            edited_company = st.selectbox("Company", all_companies_data, index=get_index(all_companies_data, lead.get('company_name'), 'Company'), format_func=lambda x: x.get("Company", ""), key="edit_company")
            
            derived_vertical_industry = ""
            if st.session_state.get('edit_company') and not companies_df.empty:
                selected_company_name = st.session_state.edit_company.get('Company')
                filtered_industry = companies_df[companies_df['Company'] == selected_company_name]['Vertical Industry']
                if not filtered_industry.empty:
                    derived_vertical_industry = filtered_industry.iloc[0]
            st.text_input("Vertical Industry", value=derived_vertical_industry, key="edit_vertical", disabled=True)
            
            service_options = get_services(st.session_state.edit_solution)
            edited_service = st.selectbox("Service", service_options, index=get_index(service_options, lead.get('service')), key="edit_service")
            edited_brand = st.selectbox("Brand", all_brands, index=get_index(all_brands, lead.get('brand'), 'Brand'), format_func=lambda x: x.get("Brand", ""), key="edit_brand")
            
            is_via_distributor_default = 0 if lead.get('distributor_name', 'Not via distributor') != "Not via distributor" else 1
            is_via_distributor_choice = st.radio("Via Distributor?", ("Yes", "No"), index=is_via_distributor_default, key="edit_is_via_distributor", horizontal=True)
            
            if is_via_distributor_choice == "Yes":
                edited_distributor = st.selectbox("Distributor", all_distributors, index=get_index(all_distributors, lead.get('distributor_name'), 'Distributor'), format_func=lambda x: x.get("Distributor", ""), key="edit_distributor_select")
            else:
                edited_distributor = "Not via distributor"

        if st.button("Save Changes", type="primary"):
            # Kumpulkan semua data yang diubah
            update_payload = {
                "uid": lead.get('uid'),
                "user": lead.get('presales_name'),
                "salesgroup_id": st.session_state.edit_sales_group,
                "sales_name": st.session_state.edit_sales_name,
                "responsible_name": st.session_state.edit_responsible.get('Responsible', ''),
                "pillar": st.session_state.edit_pillar,
                "solution": st.session_state.edit_solution,
                "service": st.session_state.edit_service,
                "brand": st.session_state.edit_brand.get('Brand', ''),
                "company_name": st.session_state.edit_company.get('Company', ''),
                "vertical_industry": st.session_state.edit_vertical,
                "distributor_name": edited_distributor.get('Distributor', '') if isinstance(edited_distributor, dict) else edited_distributor
            }
            
            with st.spinner(f"Updating opportunity..."):
                update_response = update_full_opportunity(update_payload)
                if update_response and update_response.get("status") == 200:
                    st.session_state.edit_submission_message = update_response.get("message")
                    updated_data = update_response.get("data", {})
                    new_uid = updated_data.get("uid")
                    if new_uid != uid_to_find:
                        st.session_state.edit_new_uid = new_uid
                    
                    st.session_state.lead_to_edit = None # Reset form
                    st.rerun()
                else:
                    error_message = update_response.get("message", "Failed to update.") if update_response else "Failed to update."
                    st.error(error_message)

with tab6:
    st.header("Activity Log / Audit Trail")
    st.info("This log records all creations and changes made to the opportunity data.")

    if st.button("Refresh Log"):
        st.cache_data.clear() 
    
    with st.spinner("Fetching activity log..."):
        # Panggil API untuk mendapatkan data log
        log_data = get_master('getActivityLog') 
        
        if log_data:
            df_log = pd.DataFrame(log_data)
            
            # --- LOGIKA UNTUK MENAMPILKAN DROPDOWN DAN FILTER ---
            
            # 1. Cek apakah kolom 'OpportunityName' ada di data dan tidak kosong
            if 'OpportunityName' in df_log.columns and not df_log['OpportunityName'].empty:
                
                # 2. Buat daftar nama peluang yang unik untuk dijadikan opsi dropdown
                opportunity_options = sorted(df_log['OpportunityName'].dropna().unique().tolist())
                opportunity_options.insert(0, "All Opportunities")

                # 3. Tampilkan widget dropdown/selectbox kepada pengguna
                selected_opportunity = st.selectbox(
                    "Select an Opportunity Name to track",
                    options=opportunity_options,
                    key="log_opportunity_filter"
                )

                # 4. Lakukan filter pada DataFrame berdasarkan pilihan pengguna
                if selected_opportunity != "All Opportunities":
                    df_to_display = df_log[df_log['OpportunityName'] == selected_opportunity]
                else:
                    df_to_display = df_log
            else:
                # Jika kolom OpportunityName tidak ada, tampilkan semua data tanpa filter
                df_to_display = df_log
            
            # --- AKHIR DARI LOGIKA FILTER ---

            # Proses selanjutnya menggunakan df_to_display yang sudah difilter
            if not df_to_display.empty:
                
                # ▼▼▼ BLOK YANG DIMODIFIKASI UNTUK KONVERSI WAKTU ▼▼▼
                # Urutkan dan format data waktu
                if 'Timestamp' in df_to_display.columns:
                    # Konversi ke objek datetime yang mengenali timezone (UTC)
                    df_to_display['Timestamp'] = pd.to_datetime(df_to_display['Timestamp'])
                    
                    # Urutkan berdasarkan waktu (sebelum formatnya diubah menjadi string)
                    df_to_display = df_to_display.sort_values(by="Timestamp", ascending=False)
                    
                    # Konversi ke WIB (GMT+7) dan format ulang sebagai string yang mudah dibaca
                    df_to_display['Timestamp'] = df_to_display['Timestamp'].dt.tz_convert('Asia/Jakarta').dt.strftime('%Y-%m-%d %H:%M:%S')
                # ▲▲▲ AKHIR DARI BLOK MODIFIKASI ▲▲▲

                # Ubah tipe data untuk mencegah error tampilan
                if 'OldValue' in df_to_display.columns:
                    df_to_display['OldValue'] = df_to_display['OldValue'].astype(str)
                if 'NewValue' in df_to_display.columns:
                    df_to_display['NewValue'] = df_to_display['NewValue'].astype(str)

                st.write(f"Found {len(df_to_display)} log entries for the selected filter.")
                st.dataframe(df_to_display)
            else:
                st.info("No log data found for the selected Opportunity Name.")

        else:
            st.warning("No activity log has been recorded yet.")