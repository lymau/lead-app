import streamlit as st

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
st.set_page_config(
    page_title="Presales App - SISINDOKOM",
    page_icon=":clipboard:",
    initial_sidebar_state="expanded",
    layout="wide"
)


import time
from logger_setup import logger
import backend as db
import utils

# ==============================================================================
# 2. SESSION STATE MANAGEMENT (Inisialisasi Variabel)
# ==============================================================================
if 'presales_session' not in st.session_state:
    st.session_state.presales_session = None

# Inisialisasi state untuk form dan data agar tidak error 'KeyError'
keys_to_init = [
    'product_lines', 'submission_message', 'new_uids', 
    'edit_submission_message', 'edit_new_uid', 
    'lead_sol_update', 'selected_kanban_opp_id', 
    'update_sol_msg', 'lead_to_edit'
]

for key in keys_to_init:
    if key not in st.session_state:
        if key == 'product_lines':
            st.session_state[key] = [{"id": 0}]
        else:
            st.session_state[key] = None

# ==============================================================================
# 3. HALAMAN LOGIN & AUTH
# ==============================================================================
def login_page():
    st.title("🔐 Presales App Login")
    
    # Coba ambil user list, jika DB belum connect, handle gracefully
    try:
        users_list = db.get_presales_users_list()
    except Exception as e:
        st.error(f"Gagal terhubung ke Database: {e}")
        users_list = []
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container(border=True):
            st.subheader("Please Sign In")
            
            with st.form("login_form"):
                user_input = st.selectbox("Username", options=users_list)
                pass_input = st.text_input("Password", type="password")
                
                submit = st.form_submit_button("Login", type="primary", use_container_width=True)
                
                if submit:
                    res = db.validate_presales_login(user_input, pass_input)
                    if res['status'] == 200:
                        # [LOGGING] Login Berhasil
                        logger.info(f"LOGIN SUCCESS: User '{user_input}' ({res['data'].get('access_group', 'Unknown')}) logged in.")
                        
                        st.session_state.presales_session = res['data']
                        st.rerun()
                    else:
                        # [LOGGING] Login Gagal
                        logger.warning(f"LOGIN FAILED: User '{user_input}'. Msg: {res['message']}")
                        st.error(res['message'])

def change_password_page():
    st.title("🔐 Setup New Password")
    st.info("Ini adalah login pertama Anda. Demi keamanan, silakan ubah password default Anda.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            with st.form("change_pass_form"):
                new_pass = st.text_input("New Password", type="password")
                confirm_pass = st.text_input("Confirm New Password", type="password")
                
                submit = st.form_submit_button("Update Password", type="primary")
                
                if submit:
                    if not new_pass:
                        st.error("Password tidak boleh kosong.")
                    elif new_pass != confirm_pass:
                        st.error("Password konfirmasi tidak cocok.")
                    elif len(new_pass) < 6:
                        st.warning("Password minimal 6 karakter.")
                    else:
                        # Panggil Backend
                        user_now = st.session_state.presales_session['username']
                        res = db.change_user_password(user_now, new_pass)
                        
                        if res['status'] == 200:
                            logger.info(f"PASSWORD CHANGED: User '{user_now}' updated password.")
                            st.success("✅ Password Updated! Redirecting...")
                            
                            # Update session state agar tidak diminta ganti lagi
                            st.session_state.presales_session['need_password_change'] = False
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(res['message'])

# ==============================================================================
# 4. APLIKASI UTAMA (DASHBOARD)
# ==============================================================================
def main_app():
    # Ambil data user yang sedang login
    current_user = st.session_state.presales_session
    username = current_user['username']
    access_group = current_user.get('access_group', 'Unknown')
    
    # --- Sidebar ---
    with st.sidebar:
        st.write(f"👤 **{username}**")
        st.caption(f"Group: {access_group}") 
        
        if access_group == 'TOP_MGMT':
            st.success("🌟 Full Access Mode")
        
        if st.button("Logout", type="primary"):
            logger.info(f"LOGOUT: User '{username}' logged out.")
            st.session_state.presales_session = None
            st.rerun()
        st.markdown("---")

    # --- Tabs Navigation ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Add Opportunity", "View Opportunities", "Search Opportunity", 
        "Update Opportunity", "Edit Opportunity", "Activity Log"
    ])

    # Memanggil Utils untuk konten setiap tab
    with tab1:
        utils.tab1(default_inputter=username) 

    with tab2:
        utils.tab2()

    with tab3:
        utils.tab3()

    with tab4:
        utils.tab4()

    with tab5:
        utils.tab5()

    with tab6:
        utils.tab6()

# ==============================================================================
# 5. ROUTER UTAMA (LOGIC PERBAIKAN)
# ==============================================================================
def main():
    # 1. Cek Login Session
    if not st.session_state.presales_session:
        login_page()
        return

    # 2. Cek Apakah Wajib Ganti Password?
    if st.session_state.presales_session.get('need_password_change', False):
        change_password_page()
        return

    # 3. Jika Lolos semua cek, tampilkan App Utama
    main_app()

if __name__ == "__main__":
    main()