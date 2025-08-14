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
if 'update_dismissed' not in st.session_state:
    st.session_state.update_dismissed = False

# Tampilkan notifikasi hanya jika belum ditutup
if not st.session_state.update_dismissed:
    # Gunakan st.info atau st.success untuk tampilan yang menarik
    with st.container(border=True):
        st.subheader("🚀 Update Terbaru Aplikasi! (v1.2)")
        st.markdown("""
        **Pembaruan Besar di Tab "Add Opportunity"!** Formulir kini mendukung entri multi-solusi dalam satu kali submit.
        """)
        
        # Buat tombol untuk menutup notifikasi
        if st.button("Tutup Pemberitahuan Ini", key="dismiss_update"):
            st.session_state.update_dismissed = True
            st.rerun() # Jalankan ulang script agar notifikasi langsung hilang
    st.markdown("---") # Garis pemisah

# ==============================================================================
# GET ALL MASTER DATA
# ==============================================================================

@st.cache_data(ttl=600) # Data akan di-cache selama 7 menit (450 detik)
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
    """Membersihkan data sebelum ditampilkan di st.dataframe untuk mencegah error."""
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if 'cost' in df.columns:
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0).astype(int)
    if 'selling_price' in df.columns:
        df['selling_price'] = pd.to_numeric(df['selling_price'], errors='coerce').fillna(0).astype(int)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Add Opportunity", "View Opportunities", "Search Opportunity", "Update Opportunity", "Edit Opportunity"])

# Inisialisasi session state untuk menyimpan product lines
if 'product_lines' not in st.session_state:
    st.session_state.product_lines = [{"id": 0}]
if 'submission_message' not in st.session_state:
    st.session_state.submission_message = None
if 'new_uids' not in st.session_state:
    st.session_state.new_uids = None
if 'edit_submission_message' not in st.session_state:
    st.session_state.edit_submission_message = None
if 'edit_new_uid' not in st.session_state:
    st.session_state.edit_new_uid = None

with tab1:
    st.header("Add New Opportunity (Multi-Solution)")
    st.info("Fill out the main details once, then add one or more solutions below.")

    # --- BAGIAN 1: DATA INDUK (PARENT DATA) ---
    st.subheader("Step 1: Main Opportunity Details")
    
    parent_col1, parent_col2 = st.columns(2)
    with parent_col1:
        presales_name = st.selectbox("Inputter", get_master('getPresales'), format_func=lambda x: x.get("PresalesName", "Unknown"), key="parent_presales_name")
        salesgroup_id = st.selectbox("Choose Sales Group", get_sales_groups(), key="parent_salesgroup_id")
        sales_name = st.selectbox("Choose Sales Name", get_sales_name_by_sales_group(st.session_state.get("parent_salesgroup_id")), key="parent_sales_name")

    with parent_col2:
        opportunity_name = st.selectbox("Opportunity Name", [opt.get("Desc") for opt in get_master('getOpportunities')], key="parent_opportunity_name", accept_new_options=True, index=None, placeholder="Choose or type new opportunity name")
        st.warning("IMPORTANT: Check that this opportunity wasn't submitted in Q1/Q2 to prevent duplicate entries.")
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
            
            line['responsible_name'] = st.selectbox(
                "Choose Presales Account Manager", 
                get_master('getResponsibles'), 
                format_func=lambda x: x.get("Responsible", "Unknown"), 
                key=f"responsible_{line['id']}"
            )

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
                line['cost'] = st.number_input("Cost", min_value=0, step=10000, key=f"cost_{line['id']}")
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
            st.warning(f"Terjadi masalah saat memproses daftar Presales: {e}")
    else:
        # Jika data tidak berhasil dimuat sama sekali
        st.warning("Tidak dapat memuat daftar Presales. Fitur notifikasi email tidak akan tersedia.")

    # 3. Tampilkan st.multiselect. Ini akan selalu muncul.
    # Jika presales_options kosong, widget akan muncul tapi tidak ada pilihan.
    selected_presales_names = st.multiselect(
        "Tag Presales for Push Notification (Opsional)",
        options=presales_options,
        help="Anda bisa membiarkan kolom ini kosong, atau pilih satu/lebih nama untuk notifikasi."
    )

    # 4. Proses email hanya jika ada nama yang dipilih
    if selected_presales_names:
        list_of_emails = [presales_name_to_email_map.get(name) for name in selected_presales_names if presales_name_to_email_map.get(name)]


    # 5. Tombol submit dan logikanya (tidak ada perubahan di sini)
    if st.button("Submit Opportunity and All Solutions", type="primary"):
        # Kumpulkan data induk
        parent_payload = {
            "presales_name": presales_name.get("PresalesName", ""),
            "salesgroup_id": salesgroup_id,
            "sales_name": sales_name,
            "opportunity_name": opportunity_name,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "company_name": company_name_final,
            "vertical_industry": vertical_industry_final
        }

        # Kumpulkan data product lines
        lines_payload = []
        for line in st.session_state.product_lines:
            processed_line = line.copy()
            responsible_obj = processed_line.get('responsible_name', {})
            processed_line['responsible_name'] = responsible_obj.get('Responsible', '')
            lines_payload.append(processed_line)

        # Gabungkan menjadi payload akhir
        final_payload = {
            "parent_data": parent_payload,
            "product_lines": lines_payload
        }
        
        with st.spinner("Submitting all solutions..."):
            response = add_multi_line_opportunity(final_payload)
            if response and response.get("status") == 200:
                st.session_state.submission_message = response.get("message")
                created_data = response.get('data', [])
                st.session_state.new_uids = [data.get('uid') for data in created_data]
                
                # Kirim email hanya jika list_of_emails tidak kosong
                if list_of_emails:
                    opp_id = created_data[0].get('opportunity_id', 'N/A') if created_data else 'N/A'
                    email_subject = f"New Multi-Solution Opportunity Added: {parent_payload['opportunity_name']}"
                    email_body = f"A new opportunity '{parent_payload['opportunity_name']}' with Opportunity ID '{opp_id}' and {len(lines_payload)} solution(s) has been added. Please follow up."
                    email_data = {"recipients": list_of_emails, "subject": email_subject, "body": email_body}
                    send_notification_email(email_data)
                    st.session_state.submission_message += f" | Email notification successfully sent to {len(list_of_emails)} recipient(s)."

                # Reset form dan jalankan ulang
                st.session_state.product_lines = [{"id": 0}]
                st.rerun()
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response from server'
                st.error(f"Failed to submit: {error_msg}")
                
        # --- BAGIAN 4: TAMPILKAN PESAN SUBMISSION ---
    if st.session_state.submission_message:
            st.success(st.session_state.submission_message)
            if st.session_state.new_uids:
                st.info(f"UIDs for update: {st.session_state.new_uids}")
            # Hapus pesan setelah ditampilkan agar tidak muncul lagi
            st.session_state.submission_message = None
            st.session_state.new_uids = None

with tab2:
    st.header("All Opportunities Data")
    if st.button("Refresh Opportunities"):
        with st.spinner("Fetching all opportunities..."):
            response = get_all_leads()
            if response and response.get("status") == 200:
                leads_data = response.get("data")
                if leads_data:
                    st.write(f"Found {len(leads_data)} opportunities.")
                    cleaned_df = clean_data_for_display(leads_data)
                    st.dataframe(cleaned_df)
                else:
                    st.info("No opportunities found.")
            else:
                st.error(response.get("message", "Failed to fetch all opportunities."))
                st.json(response)

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
        # show all fields but it should not be editable, except for the notes and cost fields
        st.header("Update Opportunity")
        uid = st.text_input("Enter UID to search opportunity", key="uid")
        update_button = st.button("Get Opportunity Data")
        lead = {}
        if update_button and uid:
            with st.spinner(f"Retrieving opportunity data with uid: {uid}..."):
                response = get_single_lead({"uid": uid})
                if response and response.get("status") == 200:
                    lead_data = response.get("data")
                    if lead_data:
                        lead = lead_data[0]
                        st.write(f"🆔 **Data Lead dengan UID:** {uid}")
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

                    else:
                        st.warning("No opportunity found with the given UID.")
                else:
                    st.error(response.get("message", "Failed to retrieve opportunity data."))
                    st.json(response)
                    
        with st.form(key="update_lead_form"):
            # editable fields
            notes = st.text_area("Notes", value=lead.get("Notes", ""), height=100, key="update_notes")
            cost = st.number_input("Cost", value=lead.get("Cost", 0), min_value=0, step=10000, key="update_cost")
            submit_button = st.form_submit_button("Update Opportunity")
            if submit_button:
                update_data = {
                                "uid": uid,
                                "notes": notes,
                                "cost": cost,
                            }

                with st.spinner(f"Updating opportunity {uid}..."):
                    update_response = update_lead(update_data)
                    if update_response and update_response.get("status") == 200:
                        st.success(update_response.get("message"))
                    else:
                        st.error(update_response.get("message", "Failed to update opportunity."))
                        
with tab5:
    st.header("Edit Data Entry (Error Correction)")
    st.warning("Use this page for correcting input.")

    if 'lead_to_edit' not in st.session_state:
        st.session_state.lead_to_edit = None

    # --- LANGKAH 1: CARI DATA ---
    uid_to_find = st.text_input("Enter the UID of the opportunity to be corrected:", key="uid_finder_edit")
    if st.button("Find Data to Edit"):
        st.session_state.lead_to_edit = None
        if uid_to_find:
            with st.spinner("Fetching data..."):
                response = get_single_lead({"uid": uid_to_find})
                if response and response.get("status") == 200:
                    lead_data = response.get("data")
                    if lead_data:
                        st.session_state.lead_to_edit = lead_data[0]
                        st.success("Data found. Please edit the form below.")
                    else:
                        st.error("UID not found. Please check the UID and try again.")
                else:
                    st.error("Failed to retrieve data from the database. Please try again.")
        else:
            st.warning("Please enter the UID.")
    
    if st.session_state.edit_submission_message:
        st.success(st.session_state.edit_submission_message)
        if st.session_state.edit_new_uid:
            st.info(f"IMPORTANT: The UID has been updated. The new UID is: {st.session_state.edit_new_uid}")
        # Hapus pesan setelah ditampilkan
        st.session_state.edit_submission_message = None
        st.session_state.edit_new_uid = None

    # --- LANGKAH 2: TAMPILKAN FORM EDIT JIKA DATA DITEMUKAN ---
    if st.session_state.lead_to_edit:
        lead = st.session_state.lead_to_edit
        st.markdown("---")
        st.subheader(f"Step 2: Edit Data for '{lead.get('opportunity_name', '')}'")

        # NOTE: Form dihapus untuk memungkinkan cascading dropdown interaktif
        col1, col2 = st.columns(2)
        with col1:
            all_sales_groups = get_sales_groups()
            all_responsibles = get_master('getResponsibles')
            all_pillars = get_pillars()
            all_brands = get_master('getBrands')
            def get_index(data_list, value, key=None):
                try:
                    if key: return [item.get(key) for item in data_list].index(value)
                    else: return data_list.index(value)
                except (ValueError, TypeError): return 0    
                     
            edited_responsible = st.selectbox("Presales Account Manager", all_responsibles, index=get_index(all_responsibles, lead.get('responsible_name'), 'Responsible'), format_func=lambda x: x.get("Responsible", ""), key="edit_responsible")
            
            edited_pillar = st.selectbox("Pillar", all_pillars, index=get_index(all_pillars, lead.get('pillar')), key="edit_pillar")
            solution_options = get_solutions(st.session_state.edit_pillar)
            edited_solution = st.selectbox("Solution", solution_options, index=get_index(solution_options, lead.get('solution')), key="edit_solution")
        
        with col2:
            all_companies_data = get_master('getCompanies')
            all_distributors = get_master('getDistributors')
            companies_df = pd.DataFrame(all_companies_data)
            
            service_options = get_services(st.session_state.edit_solution)
            edited_service = st.selectbox("Service", service_options, index=get_index(service_options, lead.get('service')), key="edit_service")

            edited_brand = st.selectbox("Brand", all_brands, index=get_index(all_brands, lead.get('brand'), 'Brand'), format_func=lambda x: x.get("Brand", ""), key="edit_brand")
            
            edited_company = st.selectbox(
                "Company", 
                all_companies_data, 
                index=get_index(all_companies_data, lead.get('company_name'), 'Company'), 
                format_func=lambda x: x.get("Company", ""), 
                key="edit_company"
            )

            derived_vertical_industry = ""
            if st.session_state.get('edit_company') and not companies_df.empty and 'Company' in companies_df.columns and 'Vertical Industry' in companies_df.columns:
                selected_company_name = st.session_state.edit_company.get('Company')
                filtered_industry = companies_df[companies_df['Company'] == selected_company_name]['Vertical Industry']
                if not filtered_industry.empty:
                    derived_vertical_industry = filtered_industry.iloc[0]

            st.text_input(
                "Vertical Industry", 
                value=derived_vertical_industry, 
                key="edit_vertical",
                disabled=True
            )
            
            # --- LOGIKA BARU UNTUK DISTRIBUTOR ---
            is_via_distributor_default = 1 if lead.get('distributor_name') == "Not via distributor" else 0
            is_via_distributor_choice = st.radio(
                "Is it via distributor?",
                ("Yes", "No"),
                index=is_via_distributor_default,
                key="edit_is_via_distributor"
            )

            if is_via_distributor_choice == "Yes":
                edited_distributor = st.selectbox(
                    "Distributor",
                    all_distributors,
                    index=get_index(all_distributors, lead.get('distributor_name'), 'Distributor'),
                    format_func=lambda x: x.get("Distributor", ""),
                    key="edit_distributor_select"
                )
            else:
                edited_distributor = "Not via distributor"
            # --- AKHIR LOGIKA BARU ---

        if st.button("Save Changes"):
            update_payload = {
                "uid": lead.get('uid'),
                "responsible_name": st.session_state.edit_responsible.get('Responsible', ''),
                "pillar": st.session_state.edit_pillar,
                "solution": st.session_state.edit_solution,
                "service": st.session_state.edit_service,
                "brand": st.session_state.edit_brand.get('Brand', ''),
                "company_name": st.session_state.edit_company.get('Company', ''),
                "vertical_industry": st.session_state.edit_vertical,
                "distributor_name": edited_distributor.get('Distributor', '') if isinstance(edited_distributor, dict) else edited_distributor
            }
            
            with st.spinner(f"Updating opportunity with UID: {lead.get('uid')}..."):
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
                        error_message = update_response.get("message", "Failed to update opportunity.") if update_response else "Failed to update opportunity."
                        st.error(error_message)