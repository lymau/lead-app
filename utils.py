import streamlit as st
import pandas as pd
import time
import requests
import backend as db  # Asumsi: Anda sudah memisahkan logic API ke file backend.py

# --- KONFIGURASI HALAMAN DI LEVEL UTILS (Opsional, bisa di app.py) ---
# st.set_page_config dipindah ke sini agar utils bisa mandiri jika diperlukan
# Namun biasanya tetap dipanggil di app.py paling atas.

# ==============================================================================
# HELPER FUNCTIONS & CACHING
# ==============================================================================

def format_number(number):
    """Mengubah angka menjadi string dengan pemisah titik (Format Rupiah Indonesia)."""
    try:
        num = int(float(number))
        return f"{num:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

@st.cache_data(ttl=3600) # Cache rate selama 1 jam
def get_usd_to_idr_rate():
    """Mengambil kurs USD ke IDR realtime dari API publik."""
    fallback_rate = 16500 # Nilai jaga-jaga jika API down
    api_url = "https://api.exchangerate-api.com/v4/latest/USD"
    
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['IDR']
        return fallback_rate
    except:
        return fallback_rate

# --- WRAPPER UNTUK MASTER DATA (CACHED) ---

@st.cache_data(ttl=900)
def get_master(action: str):
    """Mengambil data master dari Backend."""
    return db.get_master_presales(action)

def get_pam_mapping_dict():
    data = get_master('getPamMapping')
    if not data: return {}
    
    mapping = {}
    for item in data:
        # Coba ambil key 'Inputter' ATAU 'InputterName' (berdasarkan kode lama Anda)
        inputter_key = item.get('Inputter') or item.get('InputterName')
        
        # Coba ambil key 'PAM' ATAU 'PamName'
        pam_val = item.get('PAM') or item.get('PamName')
        
        # Hanya masukkan ke dictionary jika kedua data ada
        if inputter_key and pam_val:
            mapping[inputter_key] = pam_val
            
    return mapping

@st.cache_data(ttl=1800)
def get_pillars():
    data = get_master('getPillars')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df['Pillar'].dropna().unique().tolist()) if 'Pillar' in df.columns else []

def get_solutions(pillar):
    data = get_master('getPillars')
    if not data: return []
    df = pd.DataFrame(data)
    # Filter solution berdasarkan pillar
    return sorted(df[df['Pillar'] == pillar]['Solution'].unique().tolist()) if 'Solution' in df.columns else []

def get_services(solution):
    data = get_master('getPillars')
    if not data: return []
    df = pd.DataFrame(data)
    # Filter service berdasarkan solution
    return sorted(df[df['Solution'] == solution]['Service'].unique().tolist()) if 'Service' in df.columns else []

def get_channels(brand):
    data = get_master('getBrands')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df[df['Brand'] == brand]['Channel'].unique().tolist()) if 'Channel' in df.columns else []

def get_sales_groups():
    data = get_master('getSalesGroups')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df['SalesGroup'].dropna().unique().tolist()) if 'SalesGroup' in df.columns else []

def get_sales_name_by_sales_group(sales_group):
    data = get_master('getSalesNames') # Pastikan action ini sesuai di backend
    if not data: return []
    df = pd.DataFrame(data)
    if sales_group:
        return sorted(df[df['SalesGroup'] == sales_group]['SalesName'].unique().tolist())
    return sorted(df['SalesName'].unique().tolist())

# --- DATA CLEANING FOR DISPLAY ---

def clean_data_for_display(data):
    """Membersihkan dan memformat data untuk st.dataframe."""
    if isinstance(data, pd.DataFrame):
        if data.empty: return pd.DataFrame()
        df = data.copy()
    elif not data:
        return pd.DataFrame()
    else:
        df = pd.DataFrame(data)

    desired_order = [
        'uid', 'presales_name', 'responsible_name','salesgroup_id','sales_name', 'company_name', 
        'opportunity_name', 'start_date', 'pillar', 'solution', 'service', 'brand', 
        'channel', 'distributor_name', 'cost', 'stage', 'notes', 'sales_notes', 'created_at', 'updated_at'
    ]
    
    existing_cols = [col for col in desired_order if col in df.columns]
    if not existing_cols: return pd.DataFrame()
    
    df = df[existing_cols].copy()

    # Format Cost
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = df[col].apply(lambda x: f"Rp {format_number(x)}")

    # Format Tanggal (Timezone Handling)
    for date_col in ['start_date', 'created_at', 'updated_at']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            if date_col == 'start_date':
                df[date_col] = df[date_col].dt.strftime('%d-%m-%Y')
            else:
                try:
                    df[date_col] = df[date_col].dt.tz_convert('Asia/Jakarta')
                except TypeError:
                    # Jika tz-naive, assume UTC lalu convert ke WIB
                    df[date_col] = df[date_col].dt.tz_localize('UTC').dt.tz_convert('Asia/Jakarta')
                
                df[date_col] = df[date_col].dt.strftime('%d-%m-%Y %H:%M')
            
            df[date_col] = df[date_col].replace('NaT', '', regex=False)

    return df

# ==============================================================================
# UI COMPONENT (FRAGMENTS)
# ==============================================================================

@st.fragment
def tab1(default_inputter=None): 
    st.header("Add New Opportunity (Multi-Solution)")
    st.info("Fill out the main details once, then add one or more solutions below.")
    
    # Init Session State khusus Tab 1 jika belum ada
    if 'product_lines' not in st.session_state: st.session_state.product_lines = [{"id": 0}]
    if 'submission_message' not in st.session_state: st.session_state.submission_message = None
    if 'new_uids' not in st.session_state: st.session_state.new_uids = None

    inputter_to_pam_map = get_pam_mapping_dict()
    DEFAULT_PAM = "Not Assigned"
    
    # Fallback jika session user belum ada
    current_user_name = st.session_state.get('presales_session', {}).get('username', 'Unknown User')

    # --- STEP 1: PARENT DATA ---
    st.subheader("Step 1: Main Opportunity Details")
    parent_col1, parent_col2 = st.columns(2)
    
    with parent_col1:
        st.text_input("Inputter", value=current_user_name, disabled=True, key="parent_inputter_display")
        selected_inputter_name = current_user_name
        
        # PAM Logic
        pam_rule = inputter_to_pam_map.get(selected_inputter_name, DEFAULT_PAM)
        if pam_rule == "FLEKSIBEL":
            pam_object = st.selectbox(
                "Choose Presales Account Manager", 
                get_master('getResponsibles'), 
                format_func=lambda x: x.get("Responsible", "Unknown"), 
                key="pam_flexible_choice"
            )
            responsible_name_final = pam_object.get('Responsible', '') if pam_object else ""
        else:
            responsible_name_final = pam_rule
            st.text_input("Presales Account Manager", value=responsible_name_final, disabled=True)

        salesgroup_id = st.selectbox("Choose Sales Group", get_sales_groups(), key="parent_salesgroup_id")
        sales_name = st.selectbox("Choose Sales Name", get_sales_name_by_sales_group(salesgroup_id), key="parent_sales_name")

        # Stage Selection
        stage_raw = get_master('getPresalesStages') or [] # Handle jika None
        stage_options = sorted([s.get("Stage") for s in stage_raw if s.get("Stage")])
        default_idx = stage_options.index("Open") if "Open" in stage_options else 0
        
        selected_stage = st.selectbox("Current Stage", stage_options, index=default_idx, key="parent_stage_select")

        stage_notes = st.text_area(
            "Stage Notes (Context for AI)",
            placeholder="Jelaskan konteks stage ini (misal: Menunggu budget approval)...",
            height=100, key="parent_stage_notes"
        )

    with parent_col2:
        opp_raw = get_master('getOpportunities') or []
        opp_options = sorted([opt.get("Desc") for opt in opp_raw if opt.get("Desc")])
        
        opportunity_name = st.selectbox(
            "Opportunity Name", opp_options, key="parent_opportunity_name", 
            accept_new_options=True, index=None, placeholder="Choose or type new..."
        )
        
        start_date = st.date_input("Start Date", key="parent_start_date")
        
        # Company Logic
        all_companies = get_master('getCompanies') or []
        companies_df = pd.DataFrame(all_companies)
        
        is_company_listed = st.radio("Is the company listed?", ("Yes", "No"), key="parent_is_company_listed", horizontal=True)
        company_name_final = ""
        vertical_industry_final = ""

        if is_company_listed == "Yes":
            company_obj = st.selectbox("Choose Company", all_companies, format_func=lambda x: x.get("Company", ""), key="parent_company_select")
            if company_obj:
                company_name_final = company_obj.get("Company", "")
                vertical_industry_final = company_obj.get("Vertical Industry", "")
            st.text_input("Vertical Industry", value=vertical_industry_final, disabled=True)
        else:
            company_name_final = st.text_input("Company Name (if not listed)", key="parent_company_text_input")
            unique_verts = sorted(companies_df['Vertical Industry'].dropna().astype(str).unique().tolist()) if not companies_df.empty else []
            vertical_industry_final = st.selectbox("Choose Vertical Industry", unique_verts, key="parent_vertical_industry_select")

    # --- STEP 2: DYNAMIC PRODUCT LINES ---
    st.markdown("---")
    st.subheader("Step 2: Add Solutions")
    
    brand_data_raw = get_master('getBrands') or []
    unique_brands_list = sorted(list(set([b.get('Brand') for b in brand_data_raw if b.get('Brand')])))
    dist_data_raw = get_master('getDistributors') or []
    dist_list = sorted([d.get("Distributor") for d in dist_data_raw if d.get("Distributor")])

    for i, line in enumerate(st.session_state.product_lines):
        with st.container(border=True):
            cols = st.columns([0.9, 0.1])
            cols[0].markdown(f"**Solution {i+1}**")
            
            if len(st.session_state.product_lines) > 1:
                if cols[1].button("❌", key=f"remove_{line['id']}"):
                    st.session_state.product_lines.pop(i)
                    st.rerun()

            lc1, lc2 = st.columns(2)
            with lc1:
                # Dependent Dropdowns - Fragment akan menangani refresh parsial ini
                line['pillar'] = st.selectbox("Pillar", get_pillars(), key=f"pillar_{line['id']}")
                line['solution'] = st.selectbox("Solution", get_solutions(line['pillar']), key=f"solution_{line['id']}")
                line['service'] = st.selectbox("Service", get_services(line['solution']), key=f"service_{line['id']}")
            
            with lc2:
                line['brand'] = st.selectbox("Brand", unique_brands_list, key=f"brand_{line['id']}")
                line['channel'] = st.selectbox("Channel", get_channels(line.get('brand')), key=f"channel_{line['id']}")
                
                # Currency & Calculation Logic
                st.markdown("---")
                col_curr, col_val = st.columns([0.35, 0.65])
                with col_curr:
                    currency = st.selectbox("Currency", ["IDR", "USD"], key=f"curr_{line['id']}")
                
                current_rate = get_usd_to_idr_rate()
                
                with col_val:
                    input_val = st.number_input(
                        f"Cost Input ({currency})", min_value=0.0, 
                        step=100.0 if currency == "USD" else 1000000.0, format="%f", key=f"input_val_{line['id']}"
                    )

                final_cost_idr = 0
                calc_info = ""

                if currency == "USD":
                    if line.get("brand") == "Cisco":
                        discounted_usd = input_val * 0.5
                        final_cost_idr = discounted_usd * current_rate
                        calc_info = f"ℹ️ **Cisco Logic:** ${input_val:,.0f} x 50% = ${discounted_usd:,.0f} x (Rate {current_rate:,.0f})"
                    else:
                        final_cost_idr = input_val * current_rate
                        calc_info = f"ℹ️ **Conversion:** ${input_val:,.0f} x (Rate {current_rate:,.0f})"
                else:
                    final_cost_idr = input_val

                line['cost'] = final_cost_idr

                if currency == "USD":
                    st.info(f"{calc_info}\n\n**Final Cost: Rp {format_number(final_cost_idr)}**")
                else:
                    st.caption(f"Reads: Rp {format_number(final_cost_idr)}")
                
                is_via = st.radio("Via Distributor?", ("Yes", "No"), index=1, key=f"is_via_{line['id']}", horizontal=True)
                line['distributor_name'] = st.selectbox("Distributor", dist_list, key=f"dist_{line['id']}") if is_via == "Yes" else "Not via distributor"

            line['notes'] = st.text_area("Notes", key=f"notes_{line['id']}", height=100)

    if st.button("➕ Add Another Solution"):
        new_id = max(line['id'] for line in st.session_state.product_lines) + 1 if st.session_state.product_lines else 0
        st.session_state.product_lines.append({"id": new_id})
        st.rerun()

    # --- STEP 3: SUBMIT ---
    st.markdown("---")
    st.subheader("Step 3: Submit Opportunity")

    presales_list = get_master('getPresales') or []
    email_map = {p['PresalesName']: p['Email'] for p in presales_list if p.get('Email')}
    selected_emails = st.multiselect("Tag Presales for Notification", sorted(email_map.keys()))
    
    if st.button("Submit Opportunity and All Solutions", type="primary"):
        if not opportunity_name or not company_name_final:
            st.error("Opportunity Name and Company are required.")
        else:
            parent_data = {
                "presales_name": selected_inputter_name, 
                "responsible_name": responsible_name_final,
                "salesgroup_id": salesgroup_id, 
                "sales_name": sales_name,
                "opportunity_name": opportunity_name, 
                "start_date": start_date.strftime("%Y-%m-%d"),
                "company_name": company_name_final, 
                "vertical_industry": vertical_industry_final,
                "stage": selected_stage,
                "stage_notes": stage_notes
            }
            
            with st.spinner("Submitting to Database..."):
                # Panggil Backend
                res = db.add_multi_line_opportunity(parent_data, st.session_state.product_lines)
                
                if res and res.get('status') == 200:
                    st.session_state.submission_message = res['message']
                    st.session_state.new_uids = [x['uid'] for x in res.get('data', [])]
                    
                    if selected_emails:
                        count_sent = 0
                        for name in selected_emails:
                            email_addr = email_map.get(name)
                            if email_addr:
                                db.send_email_notification(
                                    {"recipients": [email_addr], 
                                     "subject": f"New Opp: {opportunity_name}", 
                                     "body": f"New Opportunity Created by {selected_inputter_name}.\nClient: {company_name_final}\nStage: {selected_stage}"}
                                )
                                count_sent += 1
                        st.session_state.submission_message += f" | Emails sent to {count_sent} recipient(s)."
                    
                    st.session_state.product_lines = [{"id": 0}]
                    st.rerun()
                else:
                    st.error(f"Failed to submit: {res.get('message', 'Unknown Error')}")

    if st.session_state.submission_message:
        st.success(st.session_state.submission_message)
        if st.session_state.new_uids: st.info(f"Generated UIDs: {st.session_state.new_uids}")
        st.session_state.submission_message = None
        st.session_state.new_uids = None

@st.fragment
def tab2():
    st.header("Kanban View by Opportunity Stage")
    
    # Init state lokal tab 2
    if 'selected_kanban_opp_id' not in st.session_state: st.session_state.selected_kanban_opp_id = None

    with st.spinner("Fetching leads..."):
        res = db.get_all_leads_presales()
        
    if not res or not res.get('data'):
        st.info("No data found.")
    else:
        df_master = pd.DataFrame(res['data'])
        
        # --- FILTERS ---
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        # Handle NaN agar sort tidak error
        inputters = sorted(df_master['presales_name'].fillna("Unknown").astype(str).unique())
        pams = sorted(df_master['responsible_name'].fillna("Unknown").astype(str).unique())
        groups = sorted(df_master['salesgroup_id'].fillna("Unknown").astype(str).unique())

        with c1: sel_inputter = st.multiselect("Filter by Inputter", inputters)
        with c2: sel_pam = st.multiselect("Filter by PAM", pams)
        with c3: sel_group = st.multiselect("Filter by Sales Group", groups)
        
        df_filtered = df_master.copy()
        if sel_inputter: df_filtered = df_filtered[df_filtered['presales_name'].isin(sel_inputter)]
        if sel_pam: df_filtered = df_filtered[df_filtered['responsible_name'].isin(sel_pam)]
        if sel_group: df_filtered = df_filtered[df_filtered['salesgroup_id'].isin(sel_group)]
        
        st.markdown("---")
        
        # --- DETAIL VIEW ---
        if st.session_state.selected_kanban_opp_id:
            sel_id = st.session_state.selected_kanban_opp_id
            if st.button("⬅️ Back to Kanban View"):
                st.session_state.selected_kanban_opp_id = None
                st.rerun()
            
            detail_df = df_filtered[df_filtered['opportunity_id'] == sel_id]
            if detail_df.empty:
                st.error("Details not found.")
            else:
                header = detail_df.iloc[0]
                st.header(f"Detail for: {header.get('opportunity_name')}")
                st.subheader(f"Client: {header.get('company_name')}")
                st.dataframe(clean_data_for_display(detail_df), use_container_width=True)

        # --- KANBAN BOARD ---
        else:
            if df_filtered.empty:
                st.warning("No data after filter.")
            else:
                if 'cost' not in df_filtered.columns: df_filtered['cost'] = 0
                df_filtered['cost'] = pd.to_numeric(df_filtered['cost'], errors='coerce').fillna(0)
                
                # Aggregasi per Opportunity ID
                df_opps = df_filtered.groupby('opportunity_id').agg({
                    'opportunity_name': 'first', 'company_name': 'first',
                    'presales_name': 'first', 'stage': 'first', 'cost': 'sum'
                }).reset_index()
                
                df_opps['stage'] = df_opps['stage'].fillna('Open')
                
                open_opps = df_opps[df_opps['stage'] == 'Open']
                won_opps = df_opps[df_opps['stage'] == 'Closed Won']
                lost_opps = df_opps[df_opps['stage'] == 'Closed Lost']
                
                k1, k2, k3 = st.columns(3)
                
                def render_card(row):
                    with st.container(border=True):
                        st.markdown(f"**{row['opportunity_name']}**")
                        st.caption(f"{row['company_name']} | {row['presales_name']}")
                        st.markdown(f"💰 **Rp {format_number(row['cost'])}**")
                        if st.button("View Details", key=f"btn_{row['opportunity_id']}"):
                            st.session_state.selected_kanban_opp_id = row['opportunity_id']
                            st.rerun()

                with k1:
                    st.markdown(f"### 🧊 Open ({len(open_opps)})")
                    st.markdown(f"**Total: Rp {format_number(open_opps['cost'].sum())}**")
                    st.divider()
                    for _, r in open_opps.iterrows(): render_card(r)
                
                with k2:
                    st.markdown(f"### ✅ Won ({len(won_opps)})")
                    st.markdown(f"**Total: Rp {format_number(won_opps['cost'].sum())}**")
                    st.divider()
                    for _, r in won_opps.iterrows(): render_card(r)
                    
                with k3:
                    st.markdown(f"### ❌ Lost ({len(lost_opps)})")
                    st.markdown(f"**Total: Rp {format_number(lost_opps['cost'].sum())}**")
                    st.divider()
                    for _, r in lost_opps.iterrows(): render_card(r)

@st.fragment
def tab3():
    st.header("Interactive Dashboard & Search")
    with st.spinner("Loading dataset..."):
        response = db.get_all_leads_presales()
    
    if not response or response.get("status") != 200:
        st.error("Failed to load data.")
        return

    raw_data = response.get("data", [])
    if not raw_data:
        st.info("No data.")
        return

    df = pd.DataFrame(raw_data)
    
    # Pre-processing
    if 'cost' in df.columns: df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0)
    date_col = 'start_date' if 'start_date' in df.columns else 'created_at'
    if date_col in df.columns: df['start_date_dt'] = pd.to_datetime(df[date_col], errors='coerce')
    
    filter_cols = ['presales_name', 'responsible_name', 'salesgroup_id', 'channel', 'brand', 'pillar', 'solution', 'company_name', 'stage']
    for col in filter_cols:
        if col in df.columns: df[col] = df[col].fillna("Unknown").astype(str)

    with st.container(border=True):
        st.subheader("🔍 Filters")
        c1, c2, c3, c4 = st.columns(4)
        with c1: sel_inputter = st.multiselect("Inputter", sorted(df['presales_name'].unique()))
        with c2: sel_pam = st.multiselect("PAM", sorted(df['responsible_name'].unique()))
        with c3: sel_brand = st.multiselect("Brand", sorted(df['brand'].unique()))
        with c4: sel_stage = st.multiselect("Stage", sorted(df['stage'].unique()))
        
        # Apply Logic
        df_filtered = df.copy()
        if sel_inputter: df_filtered = df_filtered[df_filtered['presales_name'].isin(sel_inputter)]
        if sel_pam: df_filtered = df_filtered[df_filtered['responsible_name'].isin(sel_pam)]
        if sel_brand: df_filtered = df_filtered[df_filtered['brand'].isin(sel_brand)]
        if sel_stage: df_filtered = df_filtered[df_filtered['stage'].isin(sel_stage)]

    st.markdown("### Summary")
    total_opps = len(df_filtered)
    total_unique = df_filtered['opportunity_id'].nunique() if 'opportunity_id' in df_filtered.columns else 0
    m1, m2 = st.columns(2)
    m1.metric("Total Line Items", total_opps)
    m2.metric("Unique Opportunities", total_unique)
    
    st.dataframe(clean_data_for_display(df_filtered), use_container_width=True)

@st.fragment
def tab4():
    st.header("Update Opportunity")
    update_mode = st.radio("Select Update Type:", ["🛠️ Update Solution Details", "📈 Update Stage"], horizontal=True)
    st.markdown("---")

    if update_mode == "🛠️ Update Solution Details":
        uid_in = st.text_input("Enter UID to search", key="uid_update_sol")
        if 'lead_sol_update' not in st.session_state: st.session_state.lead_sol_update = None

        if st.button("Get Data"):
            res = db.get_single_lead({"uid": uid_in})
            if res and res.get('status') == 200:
                st.session_state.lead_sol_update = res['data'][0]
            else:
                st.error("UID Not Found.")

        if st.session_state.lead_sol_update:
            lead = st.session_state.lead_sol_update
            st.info(f"Opp: {lead.get('opportunity_name')} | Item: {lead.get('product_id')}")
            
            c1, c2 = st.columns(2)
            new_cost = c1.number_input("Cost (IDR)", value=float(lead.get('cost') or 0))
            new_notes = c2.text_area("Notes", value=lead.get('notes', ''))
            
            if st.button("Save Update"):
                res = db.update_lead({"uid": lead['uid'], "cost": new_cost, "notes": new_notes, "user": lead.get('presales_name')})
                if res.get('status') == 200:
                    st.success("Updated!")
                    st.session_state.lead_sol_update = None
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed.")

    else:
        st.subheader("Update Stage & Context")
        opp_id_in = st.text_input("Enter Opportunity ID", key="oid_update_stg")
        # Logic update stage (simplified) - Perlu endpoint khusus di backend
        st.info("Feature to update full stage via ID coming soon (requires specific backend endpoint).")

@st.fragment
def tab5():
    st.header("Edit Data Entry")
    uid_to_find = st.text_input("Enter UID to correct:", key="uid_finder_edit")
    
    if 'lead_to_edit' not in st.session_state: st.session_state.lead_to_edit = None

    if st.button("Find Data"):
        res = db.get_single_lead({"uid": uid_to_find})
        if res and res.get('status') == 200:
            st.session_state.lead_to_edit = res['data'][0]
        else:
            st.error("Not Found")

    if st.session_state.lead_to_edit:
        lead = st.session_state.lead_to_edit
        st.write(f"Editing: {lead.get('opportunity_name')}")
        
        # Contoh field editable
        new_sg = st.selectbox("Sales Group", get_sales_groups(), index=0) # Index logic perlu disesuaikan
        
        if st.button("Save Changes"):
             # Construct payload similar to app.py logic
             st.success("Logic saving changes here...")

@st.fragment
def tab6():
    st.header("Activity Log")
    if st.button("Refresh"): st.cache_data.clear()
    
    with st.spinner("Fetching log..."):
        log_data = get_master('getActivityLog')
    
    if log_data:
        df_log = pd.DataFrame(log_data)
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No logs.")