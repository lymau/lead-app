import streamlit as st
import requests
import json
import pandas as pd

APPS_SCRIPT_API_URL = "https://script.google.com/macros/s/AKfycbzXwjAnxxUZTTSytvQEVQRiXLXLtQsZgPuBcjW2wKDgR9i1Xn5hCj_5IC7vHq79Nog/exec"

st.set_page_config(
    page_title="Leads Management - SISINDOKOM",
    page_icon=":clipboard:",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# GET ALL MASTER DATA
# ==============================================================================

@st.cache_data(ttl=3600) # Data akan di-cache selama 1 jam (3600 detik)
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

@st.cache_data(ttl=3600) # Data akan di-cache selama 1 jam (3600 detik)
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

# ==============================================================================
# ANTARMUKA STREAMLIT
# ==============================================================================

st.title("Leads Management - SISINDOKOM")
st.markdown("---")

st.info("Pastikan Anda telah mengganti `APPS_SCRIPT_API_URL` di kode dengan URL Web App Google Apps Script Anda!")

# Tab navigasi
tab1, tab2, tab3 = st.tabs(["Tambah Lead", "Lihat Semua Leads", "Cari Lead"])

with tab1:
    st.header("Tambah Lead Baru")

    observer_name = st.selectbox("Pilih Observer", get_master('getObservers'), format_func=lambda x: x.get("Observers", "Unknown"), key="observer_name")
    responsible_name = st.selectbox("Pilih Penanggung Jawab", get_master('getResponsibles'), format_func=lambda x: x.get("Responsible", "Unknown"), key="responsible_name")
    opportunity_name = st.text_input("Nama Kesempatan", key="opportunity_name")

    pillar = st.selectbox("Pilih Pilar", get_pillars(), key="pillar")
    solution = st.selectbox("Pilih Solusi", get_solutions(pillar), key="solution")
    service = st.selectbox("Pilih Layanan", get_services(solution), key="service")

    brand_name = st.selectbox("Pilih Brand", get_master('getBrands'), format_func=lambda x: x.get("Brand", "Unknown"), key="brand_name")
    channel = st.selectbox("Pilih Channel", get_channels(brand_name['Brand']), key="channel")

    is_company_listed = st.radio("Apakah perusahaan terdaftar?", ["Ya", "Tidak"], key="is_company_listed")
    if is_company_listed == "Ya":
        company_name = st.selectbox("Pilih Perusahaan", get_master('getCompanies'), format_func=lambda x: x.get("Company", "Unknown"), key="company_name")
        vertical_industry = st.selectbox("Pilih Industri Vertikal", pd.DataFrame(get_master('getCompanies'))[pd.DataFrame(get_master('getCompanies'))['Company'] == company_name['Company']]['Vertical Industry'].unique().tolist(), key="vertical_industry")
    else:
        company_name = st.text_input("Nama Perusahaan (jika tidak terdaftar)", key="company_name")
        is_vertical_industry_listed = st.radio("Apakah industri vertikal terdaftar?", ["Ya", "Tidak"], key="is_vertical_industry_listed")
        if is_vertical_industry_listed == "Ya":
            vertical_industry = st.selectbox("Pilih Industri Vertikal", pd.DataFrame(get_master('getCompanies'))["Vertical Industry"].unique().tolist(), key="vertical_industry")
        else:
            vertical_industry = st.text_input("Industri Vertikal (jika tidak terdaftar)", key="vertical_industry")

    cost = st.number_input("Biaya (Cost)", min_value=0, step=10000, key="cost")
    stage = st.selectbox("Tahap (Stage)", ["Open", "Deal Won", "Deal Lost"], key="stage")
    notes = st.text_area("Catatan (Notes)", height=100, key="notes")
    
    submitted_add = st.button("Tambah Lead")

    if submitted_add:
        if opportunity_name:
            data = {
                "observer_name": observer_name.get("Observers", ""),
                "responsible_name": responsible_name.get("Responsible", ""),
                "opportunity_name": opportunity_name,
                "pillar": pillar,
                "solution": solution,
                "service": service,
                "brand": brand_name.get("Brand", ""),
                "channel": channel,
                "company_name": company_name.get("Company", "") if isinstance(company_name, dict) else company_name,
                "vertical_industry": vertical_industry.get("Vertical Industry", "") if isinstance(vertical_industry, dict) else vertical_industry,
                "cost": cost,
                "stage": stage,
                "notes": notes
            }
            
            with st.spinner("Menambahkan lead baru..."):
                response = add_lead(data)
                if response and response.get("status") == 200:
                    st.success(response.get("message", "Lead berhasil ditambahkan!"))
                else:
                    st.error(response.get("message", "Gagal menambahkan lead."))
        else:
            st.warning("Nama Kesempatan wajib diisi.")


with tab2:
    st.header("Semua Data Leads")
    if st.button("Refresh Leads"):
        with st.spinner("Mengambil semua leads..."):
            response = get_all_leads()
            if response and response.get("status") == 200:
                leads_data = response.get("data")
                if leads_data:
                    st.write(f"Ditemukan {len(leads_data)} leads.")
                    st.dataframe(leads_data)
                else:
                    st.info("Tidak ada data leads ditemukan.")
            else:
                st.error(response.get("message", "Gagal mengambil semua leads."))
                st.json(response)

with tab3:
    st.header("Cari Lead")
    keywords = [
        "Responsible",
        "Observer",
        "Pilar",
        "Solusi",
        "Layanan",
        "Brand",
        "Perusahaan",
        "Stage",
    ]
    search_by_option = st.selectbox("Cari berdasarkan", keywords, key="search_option")

    if search_by_option == "Responsible":
        responsible_keywords = [x.get("Responsible", "Unknown") for x in get_master('getResponsibles')]
        search_query = st.selectbox("Pilih Responsible", responsible_keywords, key="search_query")
    elif search_by_option == "Observer":
        observer_keywords = [x.get("Observers", "Unknown") for x in get_master('getObservers')]
        search_query = st.selectbox("Pilih Observer", observer_keywords, key="search_query")
    elif search_by_option == "Pilar":
        pillar_keywords = get_pillars()
        search_query = st.selectbox("Pilih Pilar", pillar_keywords, key="search_query")
    elif search_by_option == "Solusi":
        pillar = st.selectbox("Pilih Pilar untuk Solusi", get_pillars(), key="search_pillar")
        solution_keywords = get_solutions(pillar)
        search_query = st.selectbox("Pilih Solusi", solution_keywords, key="search_query")
    elif search_by_option == "Layanan":
        pillar = st.selectbox("Pilih Pilar untuk Layanan", get_pillars(), key="search_pillar_service")
        solution = st.selectbox("Pilih Solusi untuk Layanan", get_solutions(pillar), key="search_solution")
        service_keywords = get_services(solution)
        search_query = st.selectbox("Pilih Layanan", service_keywords, key="search_query")
    elif search_by_option == "Brand":
        brand_keywords = [x.get("Brand", "Unknown") for x in get_master('getBrands')]
        search_query = st.selectbox("Pilih Brand", brand_keywords, key="search_query")
    elif search_by_option == "Perusahaan":
        company_keywords = [x.get("Company", "Unknown") for x in get_master('getCompanies')]
        search_query = st.selectbox("Pilih Perusahaan", company_keywords, key="search_query")
    elif search_by_option == "Stage":
        stage_keywords = ["Open", "Deal Won", "Deal Lost"]
        search_query = st.selectbox("Pilih Tahap", stage_keywords, key="search_query")

    if st.button("Cari Lead"):
        if search_query:
            search_params = {}
            if search_by_option == "Responsible":
                search_params["ResponsibleName"] = search_query
            elif search_by_option == "Observer":
                search_params["ObserverName"] = search_query
            elif search_by_option == "Pilar":
                search_params["Pillar"] = search_query
            elif search_by_option == "Solusi":
                search_params["Solution"] = search_query
            elif search_by_option == "Layanan":
                search_params["Service"] = search_query
            elif search_by_option == "Brand":
                search_params["Brand"] = search_query
            elif search_by_option == "Perusahaan":
                search_params["CompanyName"] = search_query
            elif search_by_option == "Stage":
                search_params["Stage"] = search_query
            else:
                st.error("Opsi pencarian tidak valid.")

            with st.spinner(f"Mencari lead berdasarkan {search_by_option}: {search_query}..."):
                response = get_single_lead(search_params)
                if response and response.get("status") == 200:
                    found_leads = response.get("data")
                    if found_leads:
                        st.success(f"Ditemukan {len(found_leads)} lead(s).")
                        st.dataframe(found_leads)
                    else:
                        st.info("Tidak ada lead ditemukan dengan kriteria tersebut.")
                else:
                    st.error(response.get("message", "Gagal mencari lead."))
                    st.json(response)
        else:
            st.warning("Harap masukkan query pencarian.")

