import streamlit as st

is_maintenance = st.secrets.get("general", {}).get("maintenance_mode", False)

if is_maintenance:
    st.title("🚧 Under Maintenance")
    st.warning("Aplikasi sedang dalam perbaikan. Silakan kembali lagi nanti.")
    st.stop() # Menghentikan eksekusi kode di bawahnya
    
import utils # Import file utils.py yang berisi fragments

# --- CONFIG ---
st.set_page_config(
    page_title="Presales App - SISINDOKOM",
    page_icon=":clipboard:",
    initial_sidebar_state="expanded",
    layout="wide"
)

# --- SESSION STATE INIT (Global) ---
if 'presales_session' not in st.session_state:
    # Contoh sederhana, idealnya ada halaman login
    st.session_state.presales_session = {'username': 'Presales User', 'role': 'presales'}

# --- MAIN LAYOUT ---
st.title("Presales App - SISINDOKOM (v1.6 Optimized)")
st.markdown("---")

# Render Tabs dari Utils
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Add Opportunity", 
    "Kanban View", 
    "Dashboard", 
    "Update Opportunity", 
    "Edit Entry", 
    "Activity Log"
])

# Panggil fungsi fragment dari utils.py
with tab1:
    utils.tab1() # Add Opportunity

with tab2:
    utils.tab2() # Kanban

with tab3:
    utils.tab3() # Dashboard

with tab4:
    utils.tab4() # Update

with tab5:
    utils.tab5() # Edit

with tab6:
    utils.tab6() # Logs