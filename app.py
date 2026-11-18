import streamlit as st

# ==============================================================================
# 0. STATUS PENGUNCIAN APLIKASI & MIGRASI
# ==============================================================================
APP_LOCKED = True
MIGRATION_URL = "https://sabd-app.live"
MIGRATION_DOMAIN = "sabd-app.live"

# ==============================================================================
# 1. KONFIGURASI HALAMAN
# ==============================================================================
if APP_LOCKED:
    st.set_page_config(
        page_title=f"Presales App - Migrasi ke {MIGRATION_DOMAIN}",
        page_icon=":material/lock:",
        initial_sidebar_state="collapsed",
        layout="centered"
    )
else:
    st.set_page_config(
        page_title="Presales App - SISINDOKOM",
        page_icon=":clipboard:",
        initial_sidebar_state="expanded",
        layout="wide"
    )

import time
from logger_setup import logger

if not APP_LOCKED:
    import backend as db
    import utils
else:
    db = None
    utils = None

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
            
        # ==================================================================
        # --- TAMBAHAN ADMIN TOOLS: INACTIVITY CHECKER ---
        # ==================================================================
        if username == 'Krisa Kurniawan':
            st.markdown("---")
            st.markdown("### 🛠️ Admin Tools")
            if st.button("🚨 Run 14 days Inactivity Check"):
                with st.spinner("Checking database & sending email..."):
                    res = db.check_and_remind_inactive_presales()
                    if res['status'] == 200:
                        if "Aman" in res['message']:
                            st.success(res['message'])
                        else:
                            st.warning(res['message'])
                    else:
                        st.error(res['message'])
        # ==================================================================

        st.markdown("---")
        

    # --- Tabs Navigation (Dynamic Rendering) ---
    allowed_admins = ["Krisa Kurniawan", "Maulidia Permatasari"]
    is_admin = username in allowed_admins

    # 1. Definisikan nama-nama Tab standar (Hanya 6 Tab)
    tab_names = [
        "Add Opportunity", 
        "View Opportunities", 
        "Search Opportunity", 
        "Edit and Update Opportunity", 
        "Update Stage", 
        "Activity Log"
    ]
    
    # 2. Sisipkan Tab khusus Admin HANYA JIKA user punya akses
    if is_admin:
        tab_names.append("Delete Opportunity")  # Menjadi Tab ke-7
        
    # 3. Render Tabs ke dalam sebuah list
    tabs = st.tabs(tab_names)
    
    # 4. Panggil isi dari masing-masing Tab menggunakan indeks
    with tabs[0]: utils.tab1()
    with tabs[1]: utils.tab2()
    with tabs[2]: utils.tab3()
    with tabs[3]: utils.tab4()
    with tabs[4]: utils.tab5()
    with tabs[5]: utils.tab6()
    
    # 5. Panggil tab ke-7 (indeks 6) HANYA untuk Admin
    if is_admin:
        with tabs[6]: 
            utils.tab7()

# ==============================================================================
# 5. HALAMAN APLIKASI DIKUNCI & MIGRASI
# ==============================================================================
def app_locked_page():
    """Menampilkan halaman penguncian total dan arahan migrasi ke sabd-app.live."""
    st.html(
        """
        <style>
        .block-container {
            max-width: 580px;
            padding-top: clamp(1.75rem, 6vh, 4.5rem);
            padding-bottom: 2.5rem;
        }
        .lock-header {
            display: flex;
            align-items: center;
            gap: 0.875rem;
            margin-bottom: 1.125rem;
        }
        .lock-icon-tile {
            flex-shrink: 0;
            width: 44px;
            height: 44px;
            border-radius: 10px;
            background-color: #FEF3C7;
            border: 1px solid #B45309;
            color: #92400E;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        .lock-heading-group {
            min-width: 0;
        }
        .lock-brand {
            font-size: 0.875rem;
            font-weight: 600;
            line-height: 1.3;
            margin: 0;
        }
        .lock-title {
            font-size: clamp(1.375rem, 2.5vw, 1.75rem);
            font-weight: 700;
            line-height: 1.25;
            margin: 0.25rem 0 0 0;
        }
        div[data-testid="stLinkButton"] a[data-testid="stBaseLinkButton-primary"],
        div[data-testid="stLinkButton"] a {
            background-color: #166534 !important;
            border-color: #166534 !important;
            color: #FFFFFF !important;
            min-height: 48px !important;
            font-weight: 600 !important;
            cursor: pointer !important;
            transition: background-color 0.15s ease, border-color 0.15s ease;
        }
        div[data-testid="stLinkButton"] a[data-testid="stBaseLinkButton-primary"]:hover,
        div[data-testid="stLinkButton"] a:hover {
            background-color: #14532D !important;
            border-color: #14532D !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stLinkButton"] a[data-testid="stBaseLinkButton-primary"]:active,
        div[data-testid="stLinkButton"] a:active {
            background-color: #0F3F22 !important;
            border-color: #0F3F22 !important;
            color: #FFFFFF !important;
        }
        div[data-testid="stLinkButton"] a[data-testid="stBaseLinkButton-primary"]:focus-visible,
        div[data-testid="stLinkButton"] a:focus-visible {
            outline: 2px solid transparent !important;
            box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 5px #14532D !important;
        }
        @media (prefers-reduced-motion: reduce) {
            div[data-testid="stLinkButton"] a[data-testid="stBaseLinkButton-primary"],
            div[data-testid="stLinkButton"] a {
                transition: none !important;
            }
        }
        @media (max-width: 600px) {
            .lock-header {
                align-items: flex-start;
            }
        }
        </style>
        """
    )

    with st.container(border=True):
        st.markdown(
            (
                '<div class="lock-header">'
                '<div class="lock-icon-tile" aria-hidden="true">'
                '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="2" '
                'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>'
                '<path d="M7 11V7a5 5 0 0 1 10 0v4"></path>'
                '</svg>'
                '</div>'
                '<div class="lock-heading-group">'
                '<p class="lock-brand">Presales App - SISINDOKOM</p>'
                '<h1 class="lock-title">Aplikasi ini sudah dikunci</h1>'
                '</div>'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

        st.markdown(
            f"Akses masuk dan seluruh pengelolaan data opportunity pada aplikasi lama ini sudah ditutup.\n\n"
            f"Silakan lanjutkan pekerjaan Anda dengan bermigrasi ke **{MIGRATION_DOMAIN}**."
        )

        st.link_button(
            f"Buka {MIGRATION_DOMAIN}",
            MIGRATION_URL,
            type="primary",
            use_container_width=True,
        )

        st.markdown("**Alamat aplikasi baru** (salin jika perlu):")
        st.code(MIGRATION_URL, language=None)

# ==============================================================================
# 6. ROUTER UTAMA (LOGIC PERBAIKAN)
# ==============================================================================
def main():
    # 0. Kunci total seluruh akses apabila APP_LOCKED aktif
    if APP_LOCKED:
        st.session_state.presales_session = None
        app_locked_page()
        st.stop()
        return

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