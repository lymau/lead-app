import streamlit as st
import pandas as pd
import time
import requests
import backend as db

# ==============================================================================
# 1. HELPER FUNCTIONS & CACHING
# ==============================================================================

def format_number(number):
    """Mengubah angka menjadi string dengan pemisah titik (Format Indonesia)."""
    try:
        if pd.isna(number): return "0"
        num = int(float(number))
        return f"{num:,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

@st.cache_data(ttl=3600)
def get_master(action: str):
    """Mengambil data master dari Backend."""
    return db.get_master_presales(action)

@st.cache_data(ttl=3600) 
def get_usd_to_idr_rate():
    """Mengambil kurs USD ke IDR realtime dari API publik."""
    fallback_rate = 16500 
    api_url = "https://api.exchangerate-api.com/v4/latest/USD"
    
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data['rates']['IDR']
        return fallback_rate
    except:
        return fallback_rate

def get_pam_mapping_dict():
    data = get_master('getPAMMapping')
    if not data: return {}
    return {item['Inputter']: item['PAM'] for item in data}

# Helper untuk Dropdowns
def get_channels(brand):
    """
    Mengambil list channel untuk brand tertentu.
    FIX: Memfilter nilai None, NaN, atau string kosong agar validasi tidak error
    pada Brand yang tidak memiliki channel.
    """
    data = get_master('getBrands')
    if not data: return []
    
    df = pd.DataFrame(data)
    
    # Pastikan kolom yang dicari ada
    if 'Brand' not in df.columns or 'Channel' not in df.columns:
        return []
        
    # Filter data berdasarkan Brand
    subset = df[df['Brand'] == brand]
    
    if subset.empty:
        return []
        
    # Ambil nilai unik, buang yang NaN/None
    raw_channels = subset['Channel'].dropna().unique().tolist()
    
    # FILTER PENTING: Buang string kosong ("") atau spasi (" ")
    clean_channels = [c for c in raw_channels if c and str(c).strip() != ""]
    
    return sorted(clean_channels)

def get_pillars():
    data = get_master('getPillars')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df['Pillar'].dropna().unique().tolist()) if 'Pillar' in df.columns else []

def get_solutions(pillar):
    data = get_master('getPillars')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df[df['Pillar'] == pillar]['Solution'].unique().tolist()) if 'Solution' in df.columns else []

def get_services(solution):
    data = get_master('getPillars')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df[df['Solution'] == solution]['Service'].unique().tolist()) if 'Service' in df.columns else []

def get_sales_groups():
    data = get_master('getSalesGroups')
    if not data: return []
    df = pd.DataFrame(data)
    return sorted(df['SalesGroup'].dropna().unique().tolist()) if 'SalesGroup' in df.columns else []

def get_sales_name_by_sales_group(sales_group):
    data = get_master('getSalesNames')
    if not data: return []
    df = pd.DataFrame(data)
    if sales_group:
        return sorted(df[df['SalesGroup'] == sales_group]['SalesName'].unique().tolist())
    return sorted(df['SalesName'].unique().tolist())

# ==============================================================================
# 2. DATA CLEANING & FORMATTING (CRITICAL FIX FOR DATETIME ERROR)
# ==============================================================================

def clean_data_for_display(data):
    """
    Membersihkan dan memformat data untuk st.dataframe.
    Memperbaiki error 'Can only use .dt accessor with datetimelike values'.
    """
    # 1. Handle Input Type
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
        'channel', 'distributor_name', 'cost', 'stage', 'notes', 'sales_notes', 'pillar_product', 'solution_product', 'created_at', 'updated_at'
    ]
    
    existing_cols = [col for col in desired_order if col in df.columns]
    if not existing_cols: return df
    
    df = df[existing_cols].copy()

    # 2. Format Angka (Cost)
    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = df[col].apply(lambda x: f"Rp {format_number(x)}")

    # 3. Format Tanggal (FIXED LOGIC)
    # Backend sudah menyimpan waktu WIB (+7). Kita tidak perlu convert timezone lagi.
    # Cukup pastikan tipe datanya datetime, lalu format ke string.
    for date_col in ['start_date', 'created_at', 'updated_at']:
        if date_col in df.columns:
            try:
                # A. Paksa ubah ke datetime object (Error -> NaT)
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                # B. Format ke String yang mudah dibaca
                if date_col == 'start_date':
                    # Format Tanggal Saja
                    df[date_col] = df[date_col].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else "-")
                else:
                    # Format Tanggal + Jam
                    df[date_col] = df[date_col].apply(lambda x: x.strftime('%d-%m-%Y %H:%M') if pd.notnull(x) else "-")
            except Exception:
                pass # Jika gagal, biarkan apa adanya

    return df

# ==============================================================================
# 3. TAB FUNCTIONS
# ==============================================================================

@st.fragment
def tab1(default_inputter=None): 
    st.header("Add New Opportunity (Multi-Solution)")
    st.info("Fill out the main details once, then add one or more solutions below.")
    
    # --- MAPPING KHUSUS MAINTENANCE SERVICES (UPDATED) ---
    MAINTENANCE_MAPPING = {
        "Network": [
            "SP Routing", "Optics", "WLAN and Campus LAN", "SD-WAN", 
            "Automation, Assurance & Orchestration", "xPON", "Radio Microwave", 
            "VSAT", "CGNAT", "DPI", "DDI", "Network Monitoring System", 
            "Training", "Local Material", "Others (Non Sub-Pillar)"
        ],
        "Data Center & Cloud Infrastructure": [
            "Compute", "Data Center Network Fabric", "Data Center and Application Assurance", 
            "Software Defined Data Center", "Data Storage", "Data Protection", 
            "Application Delivery", "Cloud Services", "Operating System", 
            "Data Center Orchestration", "Data Center Observability", 
            "Training", "Local Material", "Others (Non Sub-Pillar)"
        ],
        "Cyber Security": [
            "DNS Security", "Next-Gen Firewall (NGFW)", "Endpoint Protection Platform (XDR, EDR)", 
            "Secure Web Gateway", "E-Mail Security (E-Mail Gateway)", "SIEM", 
            "Network Access Control", "Multi Factor Authentication", "Security Service Edge (SSE)", 
            "Secure Access Service Edge (SASE)", "Web Application Firewall (WAF)", 
            "Privileged Access Management (PAM)", "VA", "Threat Intelligence", 
            "NDR", "SOAR", "WAAP (API Security, API Gateway)", "DLP", 
            "Penetration Test", "ITDR", "Secure SD-WAN", "Secure Browser", 
            "Fraud Detection System", "Operational Technology (OT) Security", 
            "Training", "Local Material", "Others (Non Sub-Pillar)"
        ]
    }
    
    # Load Helper Data
    inputter_to_pam_map = get_pam_mapping_dict()
    DEFAULT_PAM = "Not Assigned"

    # --- AMBIL USER DARI SESSION ---
    if 'presales_session' in st.session_state:
        current_user_name = st.session_state.presales_session['username']
    else:
        st.error("Session missing. Please login.")
        return

    # --- STEP 1: PARENT DATA (HEADER) ---
    st.subheader("Step 1: Main Opportunity Details")
    parent_col1, parent_col2 = st.columns(2)
    
    with parent_col1:
        # 1. Inputter
        st.text_input("Inputter", value=current_user_name, disabled=True, key="parent_inputter_display")
        selected_inputter_name = current_user_name
        
        # 2. PAM Logic
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

        # 3. Sales Group
        salesgroup_id = st.selectbox("Choose Sales Group", get_sales_groups(), key="parent_salesgroup_id")
        
        # 4. Sales Name
        sales_name_options = get_sales_name_by_sales_group(salesgroup_id)
        sales_name = st.selectbox("Choose Sales Name", sales_name_options, key="parent_sales_name")


    with parent_col2:
        # 6. Opportunity Name
        opp_raw = get_master('getOpportunities')
        opp_options = sorted([opt.get("Desc") for opt in opp_raw if opt.get("Desc")])
        
        opportunity_name = st.selectbox(
            "Opportunity Name", 
            opp_options, 
            key="parent_opportunity_name", 
            accept_new_options=True, 
            index=None, 
            placeholder="Choose or type new..."
        )
        
        st.caption("Format: [B2B Channel] End User - Project Name - Month Year")
        
        start_date = st.date_input("Start Date", key="parent_start_date")
        
        # 7. Company & Vertical
        all_companies = get_master('getCompanies')
        companies_df = pd.DataFrame(all_companies)
        
        is_company_listed = st.radio("Is the company listed?", ("Yes", "No"), key="parent_is_company_listed", horizontal=True)
        company_name_final = ""
        vertical_industry_final = ""

        if is_company_listed == "Yes":
            company_obj = st.selectbox(
                "Choose Company", 
                all_companies, 
                format_func=lambda x: x.get("Company", ""), 
                key="parent_company_select"
            )
            if company_obj:
                company_name_final = company_obj.get("Company", "")
                vertical_industry_final = company_obj.get("Vertical Industry", "")
            
            st.text_input("Vertical Industry", value=vertical_industry_final, disabled=True)
        else:
            company_name_final = st.text_input("Company Name (if not listed)", key="parent_company_text_input")
            if not companies_df.empty and 'Vertical Industry' in companies_df.columns:
                unique_verts = sorted(companies_df['Vertical Industry'].dropna().astype(str).unique().tolist())
            else:
                unique_verts = []
            vertical_industry_final = st.selectbox("Choose Vertical Industry", unique_verts, key="parent_vertical_industry_select")

    # --- STEP 2: DYNAMIC PRODUCT LINES ---
    st.markdown("---")
    st.subheader("Step 2: Add Solutions")
    
    brand_data_raw = get_master('getBrands')
    unique_brands_list = sorted(list(set([b.get('Brand') for b in brand_data_raw if b.get('Brand')])))
    dist_data_raw = get_master('getDistributors')
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
                # 1. Pillar
                line['pillar'] = st.selectbox("Pillar", get_pillars(), key=f"pillar_{line['id']}")
                # === KHUSUS MAINTENANCE SERVICES ===
                if line['pillar'] == "Maintenance Services":
                    st.info("🔧 Maintenance Details")
                    
                    # Pop-up Field 1: Pillar Product
                    pp_opts = list(MAINTENANCE_MAPPING.keys())
                    line['pillar_product'] = st.selectbox(
                        "Pillar Product*", 
                        pp_opts, 
                        key=f"pp_{line['id']}"
                    )
                    
                    # Pop-up Field 2: Solution Product (Cascading)
                    sp_opts = MAINTENANCE_MAPPING.get(line['pillar_product'], [])
                    line['solution_product'] = st.selectbox(
                        "Solution Product*", 
                        sp_opts, 
                        key=f"sp_{line['id']}"
                    )
                else:
                    # Reset nilai jika bukan maintenance agar database bersih
                    line['pillar_product'] = None
                    line['solution_product'] = None
                # ================================================
                # 2. Solution
                sol_opts = get_solutions(line['pillar'])
                line['solution'] = st.selectbox("Solution", sol_opts, key=f"solution_{line['id']}")
                # 3. Service
                svc_opts = get_services(line['solution'])
                line['service'] = st.selectbox("Service", svc_opts, key=f"service_{line['id']}")
            
            with lc2:
                # 4. Brand & Channel
                line['brand'] = st.selectbox("Brand", unique_brands_list, key=f"brand_{line['id']}")
                avail_channels = get_channels(line.get('brand'))

                default_idx = 0 if len(avail_channels) == 1 else None

                line['channel'] = st.selectbox(
                    "Channel*", 
                    avail_channels, 
                    index=default_idx,
                    placeholder="Select Channel...",
                    key=f"channel_{line['id']}",
                    help="Otomatis terpilih jika hanya ada satu opsi channel."
                )
                
                # 5. Currency & Cost
                st.markdown("---")
                col_curr, col_val = st.columns([0.35, 0.65])
                
                with col_curr:
                    currency = st.selectbox("Currency", ["IDR", "USD"], key=f"curr_{line['id']}")
                
                current_rate = get_usd_to_idr_rate()
                
                with col_val:
                    input_val = st.number_input(
                        f"Cost Input ({currency})", 
                        min_value=0.0, 
                        step=100.0 if currency == "USD" else 1000000.0, 
                        format="%f",
                        key=f"input_val_{line['id']}"
                    )

                final_cost_idr = 0
                calc_info = ""

                if currency == "USD":
                    if line.get("brand") == "Cisco":
                        discounted_usd = input_val * 0.5
                        final_cost_idr = discounted_usd * current_rate
                        calc_info = f"ℹ️ **Cisco Logic:** ${input_val:,.0f} x 50% Disc = ${discounted_usd:,.0f} x (Rate Rp {current_rate:,.0f})"
                    else:
                        final_cost_idr = input_val * current_rate
                        calc_info = f"ℹ️ **Conversion:** ${input_val:,.0f} x (Rate Rp {current_rate:,.0f})"
                else:
                    final_cost_idr = input_val
                    calc_info = ""

                line['cost'] = final_cost_idr

                if currency == "USD":
                    st.info(f"{calc_info}\n\n**Final Cost: Rp {format_number(final_cost_idr)}**")
                else:
                    st.caption(f"Reads: Rp {format_number(final_cost_idr)}")
                
                # 6. Distributor Logic
                is_via = st.radio("Via Distributor?", ("Yes", "No"), index=1, key=f"is_via_{line['id']}", horizontal=True)
                if is_via == "Yes":
                    line['distributor_name'] = st.selectbox("Distributor", dist_list, key=f"dist_{line['id']}")
                else:
                    line['distributor_name'] = "Not via distributor"

            # --- IMPLEMENTATION SUPPORT ---
            excluded_pillars = ["Maintenance Services", "Managed Services"]
            is_excluded = line['pillar'] in excluded_pillars
            
            if not is_excluded and "Implementation Support" not in line.get('solution', '') and final_cost_idr > 0:
                st.markdown("---")
                add_impl = st.checkbox("➕ Add 'Implementation Support' for this item?", key=f"chk_impl_{line['id']}")
                
                line['has_implementation'] = add_impl
                
                if add_impl:
                    with st.container(border=True):
                        st.markdown("###### 🔧 Implementation Details")
                        k1, k2, k3 = st.columns([0.3, 0.3, 0.4])
                        
                        with k1:
                            st.caption(f"🔗 Linked to: **{line['brand']}**")
                            impl_svc_opts = get_services("Implementation Support")
                            if not impl_svc_opts: impl_svc_opts = ["InHouse", "Distributor/Partner", "Subcont"]
                            
                            line['implementation_service'] = st.selectbox(
                                "Service Type*", 
                                impl_svc_opts, 
                                key=f"impl_svc_{line['id']}"
                            )
                            
                        with k2:
                            impl_cost_input = st.number_input(
                                "Jasa Cost (IDR)*", 
                                min_value=0.0, 
                                step=1000000.0, 
                                key=f"impl_cost_{line['id']}"
                            )
                            line['implementation_cost'] = impl_cost_input
                        
                        with k3:
                            impl_notes = st.text_input(
                                "Scope/Notes (Optional)", 
                                placeholder="e.g., Exclude Cabling, 5 Mandays...",
                                key=f"impl_note_{line['id']}"
                            )
                            line['implementation_notes_custom'] = impl_notes

                        total_bundle = final_cost_idr + impl_cost_input
                        st.markdown(f"**💰 Total Solution Cost:** :green[Rp {format_number(total_bundle)}]")
            else:
                line['has_implementation'] = False

            line['notes'] = st.text_area("Notes", key=f"notes_{line['id']}", height=100)

    if st.button("➕ Add Another Solution"):
        new_id = max(line['id'] for line in st.session_state.product_lines) + 1 if st.session_state.product_lines else 0
        st.session_state.product_lines.append({"id": new_id})
        st.rerun()

    # --- STEP 3: SUBMIT ---
    st.markdown("---")
    st.subheader("Step 3: Submit Opportunity")

    # Email Notification
    presales_data = get_master('getPresales') 
    email_map = {p['PresalesName']: p['Email'] for p in presales_data if p.get('Email')}
    recipient_options = sorted(list(email_map.keys()))
    default_recipients = [current_user_name] if current_user_name in recipient_options else []

    selected_recipient_names = st.multiselect(
        "📧 Send Email Notification To:", 
        options=recipient_options,
        default=default_recipients,
        placeholder="Choose recipients..."
    )
    target_email_list = [email_map.get(name) for name in selected_recipient_names]
    target_email_string = ", ".join(target_email_list)

    # --- TOMBOL SUBMIT ---
    if st.button("Submit Opportunity and All Solutions", type="primary"):
        
        # 1. VALIDASI CHANNEL
        channel_error = False
        for idx, item in enumerate(st.session_state.product_lines):
            brand_channels = get_channels(item.get('brand'))
            # Pastikan validasi hanya jalan jika list channel benar-benar ada isinya
            if brand_channels and not item.get('channel'):
                st.error(f"⚠️ Solution #{idx+1}: Mohon pilih **Channel** untuk Brand **{item.get('brand')}**.")
                channel_error = True
        
        if channel_error: st.stop()

        # 2. VALIDASI FIELD WAJIB
        if not opportunity_name:
            st.error("❌ Opportunity Name wajib diisi.")
            st.stop()
        if not company_name_final:
            st.error("❌ Nama Company wajib diisi/dipilih.")
            st.stop()

        # 3. AUTO-SAVE COMPANY (Jika Baru)
        if is_company_listed == "No" and company_name_final:
            with st.spinner("Saving new company to master data..."):
                db.add_master_company(company_name_final, vertical_industry_final)
            
        # 4. SIAPKAN PARENT DATA
        parent_data = {
            "presales_name": selected_inputter_name, 
            "responsible_name": responsible_name_final,
            "salesgroup_id": salesgroup_id, 
            "sales_name": sales_name,
            "opportunity_name": opportunity_name, 
            "start_date": start_date.strftime("%Y-%m-%d"),
            "company_name": company_name_final, 
            "vertical_industry": vertical_industry_final,
            "stage": "Open"
        }
        
        # 5. SIAPKAN PRODUCT LINES
        final_product_lines = []
        
        for line in st.session_state.product_lines:
            main_item = line.copy()
            ui_keys = ['has_implementation', 'implementation_cost', 'implementation_service', 'implementation_notes_custom']
            for key in ui_keys:
                main_item.pop(key, None)
            
            final_product_lines.append(main_item)
            
            if line.get('has_implementation'):
                base_note = f"Implementation for {line['solution']}"
                custom_note = line.get('implementation_notes_custom', '').strip()
                final_note = f"{base_note} - {custom_note}" if custom_note else base_note

                impl_item = {
                    "pillar": line['pillar'],
                    "solution": "Implementation Support",
                    "service": line.get('implementation_service', 'InHouse'),
                    "brand": line['brand'],
                    "channel": line.get('channel'),
                    "distributor_name": line.get('distributor_name'),
                    "cost": line.get('implementation_cost', 0),
                    "notes": final_note,
                    "id": line['id'] + 99999,
                    "pillar_product": None, "solution_product": None
                }
                final_product_lines.append(impl_item)
        
        # 6. EKSEKUSI KE BACKEND
        with st.spinner("🚀 Submitting to Database..."):
            res = db.add_multi_line_opportunity(parent_data, final_product_lines)
            
            if res['status'] == 200:
                # --- EMAIL LOGIC ---
                if target_email_list:
                    try:
                        sol_html = "<ul>" + "".join([f"<li><b>{l['solution']}</b> ({l['brand']}) - Rp {format_number(l.get('cost',0))}</li>" for l in final_product_lines]) + "</ul>"
                        email_body = f"""
                        <h3>New Opportunity Created</h3>
                        <p>
                            <b>Customer:</b> {parent_data['company_name']}<br>
                            <b>Sales:</b> {parent_data['sales_name']} ({parent_data['salesgroup_id']})<br>
                            <b>Inputter:</b> {parent_data['presales_name']}
                        </p>
                        <hr>
                        <p><b>Solution Details:</b></p>{sol_html}
                        <p style="font-size: 10px; color: grey;">Generated by Presales App</p>
                        """
                        db.send_email_notification(target_email_string, f"[New Opp] {parent_data['opportunity_name']}", email_body)
                        st.toast(f"📧 Email notification sent!", icon="✅")
                    except Exception as e:
                        st.toast(f"⚠️ Data saved but email failed: {e}", icon="⚠️")
                
                # --- SET SUCCESS MESSAGE ---
                st.session_state.submission_message = res['message']
                st.session_state.new_uids = [x['uid'] for x in res.get('data', [])]
                
                # =========================================================
                # 7. CLEAR FORM (RESET) - BAGIAN BARU
                # =========================================================
                
                # A. Reset baris produk kembali ke 1 baris kosong
                st.session_state.product_lines = [{"id": 0}]
                
                # B. Hapus key widget Header agar kembali ke default (kosong/index 0)
                keys_to_clear = [
                    "parent_opportunity_name",      # Reset Opportunity Name
                    "parent_company_select",        # Reset Company Dropdown
                    "parent_company_text_input",    # Reset Company Text Input
                    "parent_salesgroup_id",         # Reset Sales Group (balik ke index 0)
                    "parent_sales_name",            # Reset Sales Name
                    "parent_start_date",            # Reset Date
                    "pam_flexible_choice",          # Reset PAM choice
                    "parent_vertical_industry_select" # Reset Vertical
                ]
                
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]

                # C. Rerun untuk merender ulang halaman dengan state bersih
                time.sleep(1.5) 
                st.rerun()
                
            else:
                st.error(f"❌ Failed to submit: {res['message']}")

    if st.session_state.submission_message:
        st.success(st.session_state.submission_message)
        if st.session_state.new_uids: 
            st.info(f"Generated UIDs: {st.session_state.new_uids}")
        st.session_state.submission_message = None
        st.session_state.new_uids = None

@st.fragment
def tab2():
    st.header("Kanban View (Group Access)")
    
    if 'presales_session' in st.session_state:
        current_user = st.session_state.presales_session['username']
    else:
        st.error("Session expired.")
        return

    with st.spinner(f"Fetching data..."):
        res = db.get_leads_by_group_logic(current_user) 
        
    if not res['data']:
        st.info("No data found for your group.")
        return

    df_master = pd.DataFrame(res['data'])
    
    # Handle NULL for Filters
    for col in ['presales_name', 'responsible_name', 'salesgroup_id']:
        if col in df_master.columns:
            df_master[col] = df_master[col].fillna("Unknown").astype(str)
    
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1: sel_inputter = st.multiselect("Filter Inputter", sorted(df_master['presales_name'].unique()))
    with c2: sel_pam = st.multiselect("Filter PAM", sorted(df_master['responsible_name'].unique()))
    with c3: sel_group = st.multiselect("Filter Group", sorted(df_master['salesgroup_id'].unique()))
    
    df_filtered = df_master.copy()
    if sel_inputter: df_filtered = df_filtered[df_filtered['presales_name'].isin(sel_inputter)]
    if sel_pam: df_filtered = df_filtered[df_filtered['responsible_name'].isin(sel_pam)]
    if sel_group: df_filtered = df_filtered[df_filtered['salesgroup_id'].isin(sel_group)]
    
    st.markdown("---")
    
    # DETAIL VIEW
    if st.session_state.selected_kanban_opp_id:
        if st.button("⬅️ Back to Kanban View"):
            st.session_state.selected_kanban_opp_id = None
            st.rerun()
        
        sel_id = st.session_state.selected_kanban_opp_id
        detail_df = df_filtered[df_filtered['opportunity_id'] == sel_id]
        
        if not detail_df.empty:
            header = detail_df.iloc[0]
            st.header(f"{header['opportunity_name']} ({header['company_name']})")
            st.dataframe(clean_data_for_display(detail_df), use_container_width=True)
        else:
            st.warning("Details hidden by filter.")
            
    # KANBAN BOARD
    else:
        if df_filtered.empty:
            st.warning("No data.")
        else:
            # Aggregate for Kanban Cards
            df_filtered['cost'] = pd.to_numeric(df_filtered['cost'], errors='coerce').fillna(0)
            df_opps = df_filtered.groupby('opportunity_id').agg({
                'opportunity_name': 'first',
                'company_name': 'first',
                'presales_name': 'first',
                'stage': 'first',
                'cost': 'sum'
            }).reset_index()
            
            df_opps['stage'] = df_opps['stage'].fillna('Open')
            
            cols = st.columns(3)
            stages = ['Open', 'Closed Won', 'Closed Lost']
            
            for i, stage in enumerate(stages):
                with cols[i]:
                    subset = df_opps[df_opps['stage'] == stage]
                    total_val = subset['cost'].sum()
                    st.markdown(f"### {stage} ({len(subset)})")
                    st.markdown(f"**Rp {format_number(total_val)}**")
                    st.divider()
                    
                    for _, row in subset.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{row['opportunity_name']}**")
                            st.caption(f"{row['company_name']} | {row['presales_name']}")
                            st.markdown(f"💰 Rp {format_number(row['cost'])}")
                            if st.button("View", key=f"btn_{row['opportunity_id']}"):
                                st.session_state.selected_kanban_opp_id = row['opportunity_id']
                                st.rerun()

@st.fragment
def tab3():
    st.header("Interactive Dashboard & Search")
    
    # 1. Cek Session Security
    if 'presales_session' in st.session_state:
        current_user = st.session_state.presales_session['username']
    else:
        st.error("Session missing.")
        return

    # 2. Ambil Data dari Backend (Sesuai Hak Akses Group)
    with st.spinner("Loading dataset..."):
        response = db.get_leads_by_group_logic(current_user) 
    
    if not response or response.get("status") != 200:
        st.error("Failed to load data.")
    else:
        raw_data = response.get("data", [])
        if not raw_data:
            st.info("No opportunity data available for your group.")
        else:
            # Buat Master DataFrame
            df = pd.DataFrame(raw_data)
            
            # =================================================================
            # 🧹 PRE-PROCESSING DATA (Penting agar filter tidak error)
            # =================================================================
            
            # 1. Konversi Angka
            if 'cost' in df.columns:
                df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0)
            
            # 2. Konversi Tanggal (untuk filter date range)
            # Prioritas start_date, fallback ke created_at
            date_col = 'start_date' if 'start_date' in df.columns else 'created_at'
            if date_col in df.columns:
                df['start_date_dt'] = pd.to_datetime(df[date_col], errors='coerce')

            # 3. Isi nilai kosong dengan string "Unknown" agar multiselect tidak crash
            fillna_cols = [
                'presales_name', 'responsible_name', 'channel', 'brand', 'stage', 
                'salesgroup_id', 'pillar', 'solution', 'company_name', 
                'vertical_industry', 'opportunity_name', 'distributor_name'
            ]
            for col in fillna_cols:
                if col in df.columns:
                    df[col] = df[col].fillna("Unknown").astype(str)

            # =================================================================
            # 🎛️ FILTER PANEL (SLICERS)
            # =================================================================
            with st.container(border=True):
                st.subheader("🔍 Filter Panel (Slicers)")
                
                # Helper function untuk mengambil opsi unik yang sudah diurutkan
                def get_opts(col_name):
                    return sorted(df[col_name].unique()) if col_name in df.columns else []

                # Baris 1: Personil & Group
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: sel_inputter = st.multiselect("Inputter", get_opts('presales_name'), placeholder="All Inputters")
                with c2: sel_pam = st.multiselect("PAM", get_opts('responsible_name'), placeholder="All PAMs")
                with c3: sel_group = st.multiselect("Sales Group", get_opts('salesgroup_id'), placeholder="All Groups")
                with c4: sel_channel = st.multiselect("Channel", get_opts('channel'), placeholder="All Channels")
                with c5: sel_distributor = st.multiselect("Distributor", get_opts('distributor_name'), placeholder="All Dist.")

                # Baris 2: Produk & Client
                c6, c7, c8, c9, c10 = st.columns(5)
                with c6: sel_brand = st.multiselect("Brand", get_opts('brand'), placeholder="All Brands")
                with c7: sel_pillar = st.multiselect("Pillar", get_opts('pillar'), placeholder="All Pillars")
                with c8: sel_solution = st.multiselect("Solution", get_opts('solution'), placeholder="All Solutions")
                with c9: sel_client = st.multiselect("Client", get_opts('company_name'), placeholder="All Clients")
                with c10: sel_vertical = st.multiselect("Vertical", get_opts('vertical_industry'), placeholder="All Verticals")

                # Baris 3: Stage, Date, Opportunity Name
                c11, c12, c13 = st.columns([1, 2, 3])
                with c11: 
                    sel_stage = st.multiselect("Stage", get_opts('stage'), placeholder="All Stages")
                
                with c12:
                    # Filter Tanggal (Start Date)
                    min_date = df['start_date_dt'].min().date() if 'start_date_dt' in df.columns and not df['start_date_dt'].isnull().all() else None
                    max_date = df['start_date_dt'].max().date() if 'start_date_dt' in df.columns and not df['start_date_dt'].isnull().all() else None
                    
                    date_range = st.date_input(
                        "Start Date Range",
                        value=(min_date, max_date) if min_date and max_date else None,
                        help="Filter berdasarkan rentang tanggal Start Date"
                    )
                
                with c13:
                    # Search Text Manual (Opsional, pelengkap dropdown)
                    sel_opportunity = st.multiselect(
                        "Opportunity Name", 
                        get_opts('opportunity_name'), 
                        placeholder="Select Opportunity Name..."
                    )

            # =================================================================
            # 🔄 LOGIKA FILTERING (ENGINE)
            # =================================================================
            df_filtered = df.copy()

            # Terapkan filter secara bertahap
            if sel_inputter: df_filtered = df_filtered[df_filtered['presales_name'].isin(sel_inputter)]
            if sel_pam: df_filtered = df_filtered[df_filtered['responsible_name'].isin(sel_pam)]
            if sel_group: df_filtered = df_filtered[df_filtered['salesgroup_id'].isin(sel_group)]
            if sel_channel: df_filtered = df_filtered[df_filtered['channel'].isin(sel_channel)]
            if sel_distributor: df_filtered = df_filtered[df_filtered['distributor_name'].isin(sel_distributor)]
            if sel_brand: df_filtered = df_filtered[df_filtered['brand'].isin(sel_brand)]
            if sel_pillar: df_filtered = df_filtered[df_filtered['pillar'].isin(sel_pillar)]
            if sel_solution: df_filtered = df_filtered[df_filtered['solution'].isin(sel_solution)]
            if sel_client: df_filtered = df_filtered[df_filtered['company_name'].isin(sel_client)]
            if sel_vertical: df_filtered = df_filtered[df_filtered['vertical_industry'].isin(sel_vertical)]
            if sel_stage: df_filtered = df_filtered[df_filtered['stage'].isin(sel_stage)]
            
            # Filter Text Search Manual
            if sel_opportunity:
                df_filtered = df_filtered[df_filtered['opportunity_name'].isin(sel_opportunity)]
            
            if isinstance(date_range, tuple) and len(date_range) == 2 and 'start_date_dt' in df.columns:
                start_d, end_d = date_range
                mask = (df_filtered['start_date_dt'].dt.date >= start_d) & (df_filtered['start_date_dt'].dt.date <= end_d)
                df_filtered = df_filtered[mask]

            # =================================================================
            # 📊 KPI CARDS (Summary Metrics)
            # =================================================================
            st.markdown("### Summary")
            
            total_opps_lines = len(df_filtered)
            
            # Hitung Opportunity Unik (berdasarkan ID)
            total_unique_opps = df_filtered['opportunity_id'].nunique() if 'opportunity_id' in df_filtered.columns else 0

            # Hitung Customer Unik
            total_unique_customers = df_filtered['company_name'].nunique() if 'company_name' in df_filtered.columns else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Solution Lines", f"{total_opps_lines}")
            m2.metric("Unique Opportunities", f"{total_unique_opps}")
            m3.metric("Unique Customers", f"{total_unique_customers}")

            st.markdown("---")

            # =================================================================
            # 📋 DATA TABLE
            # =================================================================
            st.subheader(f"Detailed Data ({total_opps_lines} rows)")
            
            if not df_filtered.empty:
                # Gunakan fungsi cleaning yang sudah ada di utils.py
                st.dataframe(clean_data_for_display(df_filtered), use_container_width=True)
            else:
                st.warning("Tidak ada data yang cocok dengan kombinasi filter di atas.")

@st.fragment
def tab4():
    st.header("Update Solution (Cost/Notes)")
    
    uid_in = st.text_input("Enter UID to search", key="uid_update_sol")
    
    if st.button("Search UID"):
        if uid_in:
            res = db.get_lead_by_uid(uid_in)
            if res['status'] == 200:
                st.session_state.lead_sol_update = res['data'][0]
            else:
                st.error("UID Not Found")
                st.session_state.lead_sol_update = None
    
    if st.session_state.lead_sol_update:
        lead = st.session_state.lead_sol_update
        st.success(f"Editing: {lead['opportunity_name']} - {lead['product_id']}")
        
        col_curr, col_val = st.columns([0.3, 0.7])
        with col_curr:
            currency = st.selectbox("Input Currency", ["IDR", "USD"], key="upd_currency")
        
        current_rate = get_usd_to_idr_rate()
        
        with col_val:
            default_val = float(lead.get('cost') or 0) if currency == "IDR" else 0.0
            input_val = st.number_input(
                f"New Cost ({currency})", value=default_val, min_value=0.0
            )

        final_cost_idr = input_val * current_rate if currency == "USD" else input_val
        st.caption(f"Final IDR: Rp {format_number(final_cost_idr)}")
        
        new_notes = st.text_area("Notes", value=lead.get('notes', ''))
        
        if st.button("Save Update", type="primary"):
            res = db.update_lead({
                "uid": lead['uid'], 
                "cost": final_cost_idr, 
                "notes": new_notes, 
                "user": lead['presales_name'] 
            })
            if res['status'] == 200:
                st.success("Updated!")
                st.session_state.lead_sol_update = None
                time.sleep(1)
                st.rerun()
            else:
                st.error(res['message'])

@st.fragment
def tab5():
    st.header("Edit Opportunity (Full)")
    st.warning("⚠️ Perhatian: Mengubah Sales Group akan men-generate UID baru.")
    
    # --- 1. SEARCH SECTION ---
    if 'lead_to_edit' not in st.session_state:
        st.session_state.lead_to_edit = None
    if 'edit_submission_message' not in st.session_state:
        st.session_state.edit_submission_message = None
    if 'edit_new_uid' not in st.session_state:
        st.session_state.edit_new_uid = None

    uid_to_find = st.text_input("Enter UID to Edit", key="uid_finder_edit")
    
    if st.button("Find Data"):
        st.session_state.lead_to_edit = None
        st.session_state.edit_submission_message = None
        st.session_state.edit_new_uid = None
        
        if uid_to_find:
            with st.spinner("Searching..."):
                # Menggunakan db.get_single_lead sesuai import backend as db
                res = db.get_single_lead({"uid": uid_to_find})
                if res.get("status") == 200:
                    st.session_state.lead_to_edit = res.get("data")[0]
                    st.success("Data found. Please edit the form below.")
                else:
                    st.error("UID Not Found")
        else:
            st.warning("Please enter a UID.")

    # Tampilkan Pesan Sukses Update (Jika ada)
    if st.session_state.edit_submission_message:
        st.success(st.session_state.edit_submission_message)
        if st.session_state.edit_new_uid:
            st.info(f"IMPORTANT: The UID has been updated. The new UID is: {st.session_state.edit_new_uid}")
        # Reset pesan
        st.session_state.edit_submission_message = None
        st.session_state.edit_new_uid = None

    # --- 2. FORM EDIT SECTION ---
    if st.session_state.lead_to_edit:
        lead = st.session_state.lead_to_edit
        st.markdown("---")
        st.subheader(f"Step 2: Edit Data for '{lead.get('opportunity_name', '')}'")
        
        # Helper function local
        def get_index(data_list, value, key=None):
            try:
                if key: 
                    vals = [item.get(key) for item in data_list]
                    return vals.index(value)
                return data_list.index(value)
            except (ValueError, TypeError, IndexError): 
                return 0

        # Load Master Data
        all_sales_groups = get_sales_groups()
        all_responsibles = get_master('getResponsibles')
        all_pillars = get_pillars()
        all_brands = get_master('getBrands')
        all_companies_data = get_master('getCompanies')
        all_distributors = get_master('getDistributors')

        # Layout Kolom
        c1, c2 = st.columns(2)
        
        with c1:
            # 1. Sales Group & Name
            edited_sales_group = st.selectbox(
                "Sales Group", 
                all_sales_groups, 
                index=get_index(all_sales_groups, lead.get('salesgroup_id')), 
                key="edit_sales_group"
            )
            
            sales_opts = get_sales_name_by_sales_group(edited_sales_group)
            edited_sales_name = st.selectbox(
                "Sales Name", 
                sales_opts, 
                index=get_index(sales_opts, lead.get('sales_name')), 
                key="edit_sales_name"
            )
            
            # 2. PAM
            edited_responsible = st.selectbox(
                "Presales Account Manager", 
                all_responsibles, 
                index=get_index(all_responsibles, lead.get('responsible_name'), 'Responsible'), 
                format_func=lambda x: x.get("Responsible", ""), 
                key="edit_responsible"
            )

            # 3. Pillar & Solution
            edited_pillar = st.selectbox(
                "Pillar", 
                all_pillars, 
                index=get_index(all_pillars, lead.get('pillar')), 
                key="edit_pillar"
            )
            
            solution_options = get_solutions(edited_pillar)
            edited_solution = st.selectbox(
                "Solution", 
                solution_options, 
                index=get_index(solution_options, lead.get('solution')), 
                key="edit_solution"
            )

        with c2:
            # 4. Company & Vertical
            edited_company = st.selectbox(
                "Company", 
                all_companies_data, 
                index=get_index(all_companies_data, lead.get('company_name'), 'Company'), 
                format_func=lambda x: x.get("Company", ""), 
                key="edit_company"
            )
            
            # Logic Vertical Industry (Otomatis dari Company yang dipilih)
            derived_vertical_industry = ""
            if edited_company:
                derived_vertical_industry = edited_company.get('Vertical Industry', '')
            
            st.text_input("Vertical Industry", value=derived_vertical_industry, key="edit_vertical", disabled=True)

            # 5. Service & Brand
            service_options = get_services(edited_solution)
            edited_service = st.selectbox(
                "Service", 
                service_options, 
                index=get_index(service_options, lead.get('service')), 
                key="edit_service"
            )
            
            edited_brand = st.selectbox(
                "Brand", 
                all_brands, 
                index=get_index(all_brands, lead.get('brand'), 'Brand'), 
                format_func=lambda x: x.get("Brand", ""), 
                key="edit_brand"
            )

            # 6. Distributor Logic
            current_dist = lead.get('distributor_name', 'Not via distributor')
            is_via_default = 0 if current_dist != "Not via distributor" else 1
            
            is_via_distributor_choice = st.radio(
                "Via Distributor?", 
                ("Yes", "No"), 
                index=is_via_default, 
                key="edit_is_via_distributor", 
                horizontal=True
            )
            
            if is_via_distributor_choice == "Yes":
                edited_distributor = st.selectbox(
                    "Distributor", 
                    all_distributors, 
                    index=get_index(all_distributors, current_dist, 'Distributor'), 
                    format_func=lambda x: x.get("Distributor", ""), 
                    key="edit_distributor_select"
                )
                final_distributor = edited_distributor.get('Distributor') if isinstance(edited_distributor, dict) else edited_distributor
            else:
                final_distributor = "Not via distributor"

        # --- SAVE BUTTON ---
        st.markdown("---")
        if st.button("Save Full Changes", type="primary"):
            # Construct Payload
            # Gunakan lead.copy() agar field yang tidak ada di form (misal: channel) tidak hilang/menjadi None
            payload = lead.copy()
            
            # Update dengan data baru dari form
            payload.update({
                "salesgroup_id": edited_sales_group,
                "sales_name": edited_sales_name,
                "responsible_name": edited_responsible.get('Responsible') if isinstance(edited_responsible, dict) else edited_responsible,
                "pillar": edited_pillar,
                "solution": edited_solution,
                "service": edited_service,
                "brand": edited_brand.get('Brand') if isinstance(edited_brand, dict) else edited_brand,
                "company_name": edited_company.get('Company') if isinstance(edited_company, dict) else edited_company,
                "vertical_industry": derived_vertical_industry,
                "distributor_name": final_distributor,
                "user": lead.get('presales_name') # User untuk audit log
            })
            
            with st.spinner("Updating opportunity..."):
                # Panggil Backend
                res = db.update_full_opportunity(payload)
                
                if res['status'] == 200:
                    st.session_state.edit_submission_message = res.get("message")
                    
                    # Cek Ganti UID
                    new_uid = res.get("data", {}).get("uid")
                    if new_uid and new_uid != uid_to_find:
                        st.session_state.edit_new_uid = new_uid
                    
                    st.session_state.lead_to_edit = None # Tutup Form
                    st.rerun()
                else:
                    st.error(res['message'])

@st.fragment
def tab6():
    st.header("Activity Log")
    
    if 'presales_session' in st.session_state:
        current_user = st.session_state.presales_session['username']
    else:
        st.error("Session expired.")
        return

    if st.button("Refresh Log"):
        st.cache_data.clear() 
    
    with st.spinner(f"Fetching logs..."):
        log_data = db.get_activity_log_by_group(current_user)
        
    if log_data:
        df_log = pd.DataFrame(log_data)
        
        # Standardize Columns
        rename_map = {
            'timestamp': 'Timestamp', 'opportunity_name': 'Opportunity',
            'user_name': 'User', 'action': 'Action',
            'field': 'Field', 'old_value': 'Old Val', 'new_value': 'New Val'
        }
        df_log.rename(columns=rename_map, inplace=True)

        # UI Filter
        users = sorted(df_log['User'].dropna().unique().astype(str)) if 'User' in df_log.columns else []
        sel_user = st.multiselect("Filter User", users)
        
        if sel_user:
            df_log = df_log[df_log['User'].isin(sel_user)]
            
        # FORMATTING TANGGAL (FIXED)
        if 'Timestamp' in df_log.columns and not df_log.empty:
            # Paksa ke Datetime
            df_log['Timestamp'] = pd.to_datetime(df_log['Timestamp'], errors='coerce')
            # Format ke String
            df_log['Timestamp'] = df_log['Timestamp'].apply(
                lambda x: x.strftime('%d-%m-%Y %H:%M:%S') if pd.notnull(x) else "-"
            )

        st.dataframe(df_log, use_container_width=True, hide_index=True)
    else:
        st.info("No logs found.")