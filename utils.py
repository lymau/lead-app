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
    
    if 'Brand' not in df.columns or 'Channel' not in df.columns:
        return []
        
    subset = df[df['Brand'] == brand]
    if subset.empty:
        return []
        
    raw_channels = subset['Channel'].dropna().unique().tolist()
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
# 2. DATA CLEANING & FORMATTING
# ==============================================================================

def clean_data_for_display(data):
    """
    Membersihkan dan memformat data untuk st.dataframe.
    Memperbaiki error 'Can only use .dt accessor with datetimelike values'.
    """
    if isinstance(data, pd.DataFrame):
        if data.empty: return pd.DataFrame()
        df = data.copy()
    elif not data:
        return pd.DataFrame()
    else:
        df = pd.DataFrame(data)

    desired_order = [
        'uid', 'presales_name', 'responsible_name','salesgroup_id','sales_name', 'route_to_market','company_name', 
        'opportunity_name', 'start_date', 'pillar', 'solution', 'service', 'brand', 
        'channel', 'distributor_name', 'cost', 'stage', 'notes', 'sales_notes', 'pillar_product', 'solution_product', 'created_at', 'updated_at'
    ]
    
    existing_cols = [col for col in desired_order if col in df.columns]
    if not existing_cols: return df
    
    df = df[existing_cols].copy()

    for col in ['cost', 'selling_price']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[col] = df[col].apply(lambda x: f"Rp {format_number(x)}")

    for date_col in ['start_date', 'created_at', 'updated_at']:
        if date_col in df.columns:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                if date_col == 'start_date':
                    df[date_col] = df[date_col].apply(lambda x: x.strftime('%d-%m-%Y') if pd.notnull(x) else "-")
                else:
                    df[date_col] = df[date_col].apply(lambda x: x.strftime('%d-%m-%Y %H:%M') if pd.notnull(x) else "-")
            except Exception:
                pass
    return df

# ==============================================================================
# 3. TAB FUNCTIONS
# ==============================================================================

@st.fragment
def tab1(default_inputter=None): 
    st.markdown("""
        <style>
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #28a745 !important;
            border-color: #28a745 !important;
            color: white !important; 
        }
        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background-color: #218838 !important;
            border-color: #1e7e34 !important;
        }
        div[data-testid="stButton"] > button[kind="primary"]:focus {
            box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.5) !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.header("Add New Opportunity (Multi-Solution)")
    st.info("Fill out the main details once, then add one or more solutions below.")
    
    # --- MAPPING KHUSUS MAINTENANCE SERVICES ---
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
        ],
        "Others (Non-Pillar)" : [
            "Others (Non Sub-Pillar)", 'Local Material', "Training"
        ]
    }
    
    # Load Helper Data
    inputter_to_pam_map = get_pam_mapping_dict()
    DEFAULT_PAM = "Not Assigned"

    # --- AMBIL USER DARI SESSION ---
    current_user_name = ""
    current_access_group = ""
    
    if 'presales_session' in st.session_state:
        current_user_name = st.session_state.presales_session['username']
        current_access_group = st.session_state.presales_session.get('access_group', '')
    else:
        st.error("Session missing. Please login.")
        return

    # --- STEP 1: PARENT DATA (HEADER) ---
    st.subheader("Step 1: Main Opportunity Details")
    parent_col1, parent_col2 = st.columns(2)
    
    with parent_col1:
        # --- SAFETY INJECTION ---
        selected_inputter_name = current_user_name
        responsible_name_final = ""

        # ==============================================================
        # LOGIKA 1: UNLOCK UNTUK TOP_MGMT
        # ==============================================================
        if current_access_group == 'TOP_MGMT':
            st.info("🔓 Top Management Override")
            
            all_presales_raw = get_master('getPresales')
            presales_list = sorted(list(set([p.get('PresalesName') for p in all_presales_raw if isinstance(p, dict) and p.get('PresalesName')])))
            
            all_responsibles_raw = get_master('getResponsibles')
            responsibles_list = sorted(list(set([r.get('Responsible') for r in all_responsibles_raw if isinstance(r, dict) and r.get('Responsible')])))
            
            default_idx = presales_list.index(current_user_name) if current_user_name in presales_list else 0
            
            selected_inputter_name = st.selectbox(
                "Inputter (Override)", 
                options=presales_list, 
                index=default_idx, 
                key="parent_inputter_override"
            )
            
            responsible_name_final = st.selectbox(
                "Presales Account Manager (Override)", 
                options=responsibles_list, 
                key="parent_pam_override"
            )

        # ==============================================================
        # LOGIKA 2: UNLOCK UNTUK TEAM LEAD (Otto Erdianthoko / DC_TEAM)
        # ==============================================================
        elif current_user_name == 'Otto Erdianthoko' or current_access_group == 'DC_TEAM':
            st.info("🔓 Team Lead Override (DC TEAM)")
            
            all_presales_raw = get_master('getPresales')
            dc_team_list = []
            
            if all_presales_raw:
                for p in all_presales_raw:
                    if isinstance(p, dict):
                        p_name = p.get('PresalesName')
                        p_group = p.get('Group') or p.get('AccessGroup')
                        if p_name and p_group == 'DC_TEAM':
                            dc_team_list.append(p_name)
            
            if not dc_team_list:
                dc_team_list = ["Otto Erdianthoko", "Beni Septian", "Budi Ezeddin", "Kriswanto Purwoko", "Nanda Bintarto"]
                
            dc_team_list = sorted(list(set([str(name) for name in dc_team_list if name])))
            default_idx = dc_team_list.index(current_user_name) if current_user_name in dc_team_list else 0
            
            selected_inputter_name = st.selectbox(
                "Inputter (DC Team Override)", 
                options=dc_team_list, 
                index=default_idx, 
                key="parent_inputter_override_dc"
            )
            
            pam_rule = inputter_to_pam_map.get(selected_inputter_name, DEFAULT_PAM)
            if pam_rule == "FLEKSIBEL":
                responsibles_data = get_master('getResponsibles')
                pam_object = st.selectbox(
                    "Choose Presales Account Manager", 
                    options=responsibles_data if responsibles_data else [], 
                    format_func=lambda x: x.get("Responsible", "Unknown") if isinstance(x, dict) else str(x), 
                    key="pam_flexible_choice_dc"
                )
                responsible_name_final = pam_object.get('Responsible', '') if isinstance(pam_object, dict) else ""
            else:
                responsible_name_final = pam_rule
                st.text_input("Presales Account Manager", value=responsible_name_final, disabled=True, key="pam_locked_dc")

        # ==============================================================
        # LOGIKA 3: AUTO-LOCK UNTUK USER BIASA (ENT_1, ENT_2, SP1A, dll)
        # ==============================================================
        else:
            st.text_input("Inputter", value=current_user_name, disabled=True, key="parent_inputter_display")
            selected_inputter_name = current_user_name
            
            pam_rule = inputter_to_pam_map.get(selected_inputter_name, DEFAULT_PAM)
            if pam_rule == "FLEKSIBEL":
                responsibles_data = get_master('getResponsibles')
                pam_object = st.selectbox(
                    "Choose Presales Account Manager", 
                    options=responsibles_data if responsibles_data else [], 
                    format_func=lambda x: x.get("Responsible", "Unknown") if isinstance(x, dict) else str(x), 
                    key="pam_flexible_choice"
                )
                responsible_name_final = pam_object.get('Responsible', '') if isinstance(pam_object, dict) else ""
            else:
                responsible_name_final = pam_rule
                st.text_input("Presales Account Manager", value=responsible_name_final, disabled=True, key="pam_locked_biasa")

        # -----------------------------------------------------------
        # 3. Sales Group
        # -----------------------------------------------------------
        all_sg_options = get_sales_groups()
        
        
        if current_access_group == 'ENT_1':
            final_sg_options = [sg for sg in all_sg_options if sg in ['ENT1', 'SP1B']]
            if not final_sg_options: final_sg_options = all_sg_options
        elif current_access_group == '2ND_TIER':
            final_sg_options = ['SP2B']
        elif current_access_group == 'ENT_2':
            final_sg_options = ['ENT2']
        else:
            final_sg_options = all_sg_options
            
        salesgroup_id = st.selectbox("Choose Sales Group", final_sg_options, key="parent_salesgroup_id")
        
        # 4. Sales Name
        sales_name_options = get_sales_name_by_sales_group(salesgroup_id)
        sales_name = st.selectbox("Choose Sales Name", sales_name_options, key="parent_sales_name")

    # 1. Route to Market
    with parent_col2:
        # --- 1. TENTUKAN MODE DI AWAL SEBELUM INPUT APAPUN ---
        opp_entry_mode = st.radio(
            "Opportunity Entry Mode", 
            ("📝 Create New Opportunity", "🔗 Join Existing Opportunity"), 
            horizontal=True, 
            key="parent_opp_entry_mode"
        )
        
        st.markdown("---")
        
        # Variabel penampung default agar tidak error saat dikirim ke Payload backend
        opportunity_name_final = ""
        company_name_final = ""
        vertical_industry_final = ""
        final_route = "Direct"
        start_date = pd.Timestamp.now().date() 
        is_company_listed = "Yes" 

        if opp_entry_mode == "🔗 Join Existing Opportunity":
            # ==========================================
            # MODE JOIN: HANYA TAMPILKAN DROPDOWN OPP
            # ==========================================
            opp_raw = get_master('getOpportunities')
            opp_options = sorted([opt.get("Desc") for opt in opp_raw if opt.get("Desc")])
            
            opportunity_name_final = st.selectbox(
                "Select Existing Opportunity", 
                options=opp_options, 
                key="parent_existing_opportunity_name", 
                index=None, 
                placeholder="Choose an existing project..."
            )
            
            start_date = st.date_input("Start Date", key="parent_start_date_existing")
            
            # --- MAGIC PARSING: Ekstrak identitas Parent dari string namanya! ---
            if opportunity_name_final:
                try:
                    # Membedah string misal: "[Telkom] AAF International - Project - April 2026"
                    parsed_route = opportunity_name_final.split(']')[0].replace('[', '').strip()
                    parsed_company = opportunity_name_final.split(']')[1].split('-')[0].strip()
                    
                    final_route = parsed_route
                    company_name_final = parsed_company
                    vertical_industry_final = "Auto-Synced with Parent" 
                    
                    st.success(f"🔗 **Auto-Synced with Parent Data:**\n* Route: **{final_route}**\n* Company: **{company_name_final}**")
                except:
                    st.warning("⚠️ Format opportunity lama tidak standar. Harap hubungi Admin.")

        else:
            # ==========================================
            # MODE CREATE NEW: TAMPILKAN FORM LENGKAP
            # ==========================================
            sales_approach = st.radio("Route to Market?", ("Direct", "B2B Channel"), horizontal=True, key="parent_route_to_market")
            
            b2b_channel_selected = None
            if sales_approach == "B2B Channel":
                b2b_channel_selected = st.selectbox(
                    "Select B2B Channel", 
                    ["Telkom", "iForte", "Penataran", "Icon+", "IOH", "XL", "Fiberstar", "Lintasarta", "Jasnikom", "PGASCOM", "Biznet", "Others"],
                    key="parent_b2b_channel"
                )
                company_label = "End User"
                is_listed_label = "Is the End User listed?"
                route_string = b2b_channel_selected
                final_route = b2b_channel_selected # Set variabel final
            else:
                company_label = "Company"
                is_listed_label = "Is the company listed?"
                route_string = "Direct"
                final_route = "Direct"             # Set variabel final

            # --- Pilih Company ---
            all_companies = get_master('getCompanies')
            companies_df = pd.DataFrame(all_companies)
            
            is_company_listed = st.radio(is_listed_label, ("Yes", "No"), key="parent_is_company_listed", horizontal=True)

            if is_company_listed == "Yes":
                company_obj = st.selectbox(
                    f"Choose {company_label}", 
                    all_companies, 
                    format_func=lambda x: x.get("Company", ""), 
                    key="parent_company_select"
                )
                if company_obj:
                    company_name_final = company_obj.get("Company", "")
                    vertical_industry_final = company_obj.get("Vertical Industry", "")
                st.text_input("Vertical Industry", value=vertical_industry_final, disabled=True)
            else:
                company_name_final = st.text_input(f"New {company_label} Name", key="parent_company_text_input")
                if not companies_df.empty and 'Vertical Industry' in companies_df.columns:
                    unique_verts = sorted(companies_df['Vertical Industry'].dropna().astype(str).unique().tolist())
                else:
                    unique_verts = []
                vertical_industry_final = st.selectbox("Choose Vertical Industry", unique_verts, key="parent_vertical_industry_select")

            # --- Isi Project Name & Auto Generate ---
            project_name = st.text_input("Project Name (Core Activity)", placeholder="e.g., Data Center Refresh", key="parent_new_project_name")
            start_date = st.date_input("Start Date", key="parent_start_date_new")
            month_year_string = start_date.strftime("%B %Y")
            
            if route_string and company_name_final and project_name and start_date:
                opportunity_name_final = f"[{route_string}] {company_name_final} - {project_name} - {month_year_string}"
                st.success(f"📌 **Generated Opportunity Name:**\n\n`{opportunity_name_final}`")
            else:
                st.info("💡 Fill out Company and Project Name to auto-generate the Opportunity Name.")

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
                    pp_opts = list(MAINTENANCE_MAPPING.keys())
                    line['pillar_product'] = st.selectbox("Pillar Product*", pp_opts, key=f"pp_{line['id']}")
                    sp_opts = MAINTENANCE_MAPPING.get(line['pillar_product'], [])
                    line['solution_product'] = st.selectbox("Solution Product*", sp_opts, key=f"sp_{line['id']}")
                else:
                    line['pillar_product'] = None
                    line['solution_product'] = None
                
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
                line['channel'] = st.selectbox("Channel*", avail_channels, index=default_idx, placeholder="Select Channel...", key=f"channel_{line['id']}")
                
                # 5. Currency & Cost
                st.markdown("---")
                col_curr, col_val = st.columns([0.35, 0.65])
                with col_curr:
                    currency = st.selectbox("Currency", ["IDR", "USD"], key=f"curr_{line['id']}")
                current_rate = get_usd_to_idr_rate()
                with col_val:
                    input_val = st.number_input(f"Cost Input ({currency})", min_value=0.0, step=100.0 if currency == "USD" else 1000000.0, format="%f", key=f"input_val_{line['id']}")

                final_cost_idr = 0
                calc_info = ""

                if currency == "USD":
                    if line.get("brand") == "Cisco":
                        discounted_usd = input_val * 0.4
                        final_cost_idr = discounted_usd * current_rate
                        calc_info = f"ℹ️ **Cisco Logic:** ${input_val:,.0f} x 50% Disc = ${discounted_usd:,.0f} x (Rate Rp {current_rate:,.0f})"
                    else:
                        final_cost_idr = input_val * current_rate
                        calc_info = f"ℹ️ **Conversion:** ${input_val:,.0f} x (Rate Rp {current_rate:,.0f})"
                else:
                    final_cost_idr = input_val
                
                line['cost'] = final_cost_idr

                if currency == "USD":
                    st.info(f"{calc_info}\n\n**Final Cost: Rp {format_number(final_cost_idr)}**")
                else:
                    st.caption(f"Reads: Rp {format_number(final_cost_idr)}")
                
        
            is_via = st.radio("Via Distributor?", ("Yes", "No"), index=1, key=f"is_via_{line['id']}", horizontal=True)
            if is_via == "Yes":
                # --- START OF NEW LOGIC ---
                
                # 6.a Ask if the distributor is already in the list
                is_dist_listed = st.radio("Is the distributor listed?", ("Yes", "No"), index=0, key=f"is_dist_listed_{line['id']}", horizontal=True)
                
                if is_dist_listed == "Yes":
                    # Standard behavior: Select from the list
                    line['distributor_name'] = st.selectbox(
                        "Select Distributor", 
                        options=dist_list, 
                        key=f"dist_{line['id']}"
                    )
                else:
                    # New behavior: Allow manual entry
                    new_dist_name = st.text_input(
                        "Enter New Distributor Name", 
                        key=f"new_dist_{line['id']}"
                    ).strip()
                    
                    # We assign it to the line dictionary
                    line['distributor_name'] = new_dist_name
                    
                    # Save to database immediately if the user has typed something
                    # Using a button ensures it doesn't trigger on every keystroke
                    if new_dist_name:
                        if st.button(f"Save '{new_dist_name}' to Database", key=f"save_dist_btn_{line['id']}"):
                            with st.spinner("Saving new distributor..."):
                                # Call your backend to add the name
                                res = db.add_master_distributor(new_dist_name) 
                                if res['status'] == 200:
                                    st.success("New distributor added successfully!")
                                    st.rerun() # Refresh to update the master list
                                else:
                                    st.error(res['message'])
                                    
                # --- END OF NEW LOGIC ---

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
                            line['implementation_service'] = st.selectbox("Service Type*", impl_svc_opts, key=f"impl_svc_{line['id']}")
                        with k2:
                            impl_cost_input = st.number_input("Jasa Cost (IDR)*", min_value=0.0, step=1000000.0, key=f"impl_cost_{line['id']}")
                            line['implementation_cost'] = impl_cost_input
                        with k3:
                            impl_notes = st.text_input("Scope/Notes (Optional)", placeholder="e.g., Exclude Cabling...", key=f"impl_note_{line['id']}")
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

    presales_data = get_master('getPresales') 
    email_map = {p['PresalesName']: p['Email'] for p in presales_data if p.get('Email')}
    recipient_options = sorted(list(email_map.keys()))
    default_recipients = [current_user_name] if current_user_name in recipient_options else []

    selected_recipient_names = st.multiselect(
        "📧 Send Email Notification To:", options=recipient_options, default=default_recipients, placeholder="Choose recipients..."
    )

    if st.button("Submit Opportunity and All Solutions", type="primary"):
        channel_error = False
        for idx, item in enumerate(st.session_state.product_lines):
            brand_channels = get_channels(item.get('brand'))
            if brand_channels and not item.get('channel'):
                st.error(f"⚠️ Solution #{idx+1}: Mohon pilih **Channel** untuk Brand **{item.get('brand')}**.")
                channel_error = True
        if channel_error: st.stop()

        if not company_name_final:
            st.error("❌ Nama Company wajib diisi/dipilih.")
            st.stop()
        if not opportunity_name_final: # <--- Cek variabel ini
            st.error("❌ Opportunity Name wajib diisi atau dibentuk secara sempurna.")
            st.stop()

        if is_company_listed == "No" and company_name_final:
            with st.spinner("Saving new company to master data..."):
                db.add_master_company(company_name_final, vertical_industry_final)
                
        # final_route = "Direct" if sales_approach == "Direct" else b2b_channel_selected
            
        parent_data = {
            "presales_name": selected_inputter_name, 
            "responsible_name": responsible_name_final,
            "salesgroup_id": salesgroup_id, 
            "sales_name": sales_name,
            "opportunity_name": opportunity_name_final,  # <--- Gunakan Variabel Final
            "start_date": start_date.strftime("%Y-%m-%d"),
            "company_name": company_name_final, 
            "vertical_industry": vertical_industry_final, 
            "stage": "Open",
            "route_to_market": final_route
        }
        
        final_product_lines = []
        # --- LOGIKA BARU: AUTO-CC CHANNEL PIC ---
        auto_cc_emails = set() # Menggunakan set agar tidak ada email duplikat
        
        for line in st.session_state.product_lines:
            main_item = line.copy()
            
            # Deteksi Channel PIC dan ambil emailnya jika ada di database Presales
            pic_name = main_item.get('channel')
            if pic_name and pic_name in email_map:
                auto_cc_emails.add(email_map[pic_name])

            for key in ['has_implementation', 'implementation_cost', 'implementation_service', 'implementation_notes_custom']:
                main_item.pop(key, None)
            final_product_lines.append(main_item)
            
            if line.get('has_implementation'):
                base_note = f"Implementation for {line['solution']}"
                custom_note = line.get('implementation_notes_custom', '').strip()
                final_note = f"{base_note} - {custom_note}" if custom_note else base_note
                final_product_lines.append({
                    "pillar": line['pillar'], "solution": "Implementation Support", "service": line.get('implementation_service', 'InHouse'),
                    "brand": line['brand'], "channel": line.get('channel'), "distributor_name": line.get('distributor_name'),
                    "cost": line.get('implementation_cost', 0), "notes": final_note, "id": line['id'] + 99999,
                    "pillar_product": None, "solution_product": None
                })
        
        # --- PENGGABUNGAN EMAIL ---
        # Gabungkan email yang dipilih manual di UI dengan email PIC yang terdeteksi
        manual_email_list = [email_map.get(name) for name in selected_recipient_names if email_map.get(name)]
        final_email_set = set(manual_email_list).union(auto_cc_emails)
        target_email_string = ", ".join(final_email_set)
        
        with st.spinner("🚀 Submitting to Database..."):
            res = db.add_multi_line_opportunity(parent_data, final_product_lines)
            if res['status'] == 200:
                # Modifikasi: Kirim email jika target_email_string tidak kosong
                if target_email_string:
                    try:
                        sol_html = "<ul>" + "".join([f"<li><b>{l['solution']}</b> ({l['brand']}) - Rp {format_number(l.get('cost',0))}</li>" for l in final_product_lines]) + "</ul>"
                        email_body = f"<h3>New Opportunity Created</h3><p><b>Customer:</b> {parent_data['company_name']}<br><b>Sales:</b> {parent_data['sales_name']} ({parent_data['salesgroup_id']})<br><b>Inputter:</b> {parent_data['presales_name']}</p><hr><p><b>Solution Details:</b></p>{sol_html}<p style='font-size: 10px; color: grey;'>Generated by Presales App</p>"
                        
                        db.send_email_background(target_email_string, f"[New Opp] {parent_data['opportunity_name']}", email_body)
                        st.toast(f"📧 Email notification sent to: {target_email_string}", icon="✅")
                    except Exception as e: 
                        st.toast(f"⚠️ Data saved but email failed: {e}", icon="⚠️")
                
                st.session_state.submission_message = res['message']
                st.session_state.new_uids = [x['uid'] for x in res.get('data', [])]
                
                keys_to_clear = [
                    "parent_opp_entry_mode", "parent_existing_opportunity_name", "parent_new_project_name", 
                    "parent_start_date_existing", "parent_start_date_new",
                    "parent_company_select", "parent_company_text_input", 
                    "parent_salesgroup_id", "parent_sales_name",  
                    "pam_flexible_choice", "parent_vertical_industry_select",
                    "parent_inputter_override", "parent_pam_override",
                    "parent_inputter_override_dc", "pam_flexible_choice_dc",
                    "parent_route_to_market", "parent_b2b_channel", "parent_is_company_listed"
                ]
                for key in keys_to_clear:
                    if key in st.session_state: 
                        del st.session_state[key]
                        
                prefixes_to_clear = [
                    "pillar_", "pp_", "sp_", "solution_", "service_", "brand_", 
                    "channel_", "curr_", "input_val_", "is_via_", "is_dist_listed_", 
                    "dist_", "new_dist_", "chk_impl_", "impl_svc_", "impl_cost_", 
                    "impl_note_", "notes_"
                ]
            
                for key in list(st.session_state.keys()):
                    if any(key.startswith(prefix) for prefix in prefixes_to_clear):
                        del st.session_state[key]
                st.session_state.product_lines = [{"id": 0}]
                time.sleep(2) 
                st.rerun()
            else:
                st.error(f"❌ Failed to submit: {res['message']}")

    if st.session_state.submission_message:
        st.success(st.session_state.submission_message)
        if st.session_state.new_uids: st.info(f"Generated UIDs: {st.session_state.new_uids}")
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
        
    if res.get('status') != 200:
        st.error(f"Database Error: {res.get('message')}")
        return
        
    if not res.get('data'):
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
    
    # =================================================================
    # 1. DETAIL VIEW
    # =================================================================
    if st.session_state.selected_kanban_opp_id:
        if st.button("⬅️ Back to Kanban View"):
            st.session_state.selected_kanban_opp_id = None
            st.rerun()
        
        sel_id = st.session_state.selected_kanban_opp_id
        detail_df = df_filtered[df_filtered['opportunity_id'] == sel_id]
        
        if not detail_df.empty:
            header = detail_df.iloc[0]
            st.header(f"{header['opportunity_name']} ({header['company_name']})")
            
            # --- FIX: Tampilkan Grand Total di Detail View ---
            total_kalkulasi = pd.to_numeric(detail_df['cost'], errors='coerce').fillna(0).sum()
            st.info(f"**💰 Grand Total Cost:** Rp {format_number(total_kalkulasi)}")
            # -------------------------------------------------
            
            st.dataframe(clean_data_for_display(detail_df), use_container_width=True)
        else:
            st.warning("Details hidden by filter.")
            
    # =================================================================
    # 2. KANBAN BOARD
    # =================================================================
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
                            st.caption(f"🏢 {row['company_name']} | 👤 {row['presales_name']}")
                            
                            # --- FIX: Memunculkan Rincian Detail di Kanban Card ---
                            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                            
                            # Tarik data item khusus untuk opportunity ini
                            items_in_opp = df_filtered[df_filtered['opportunity_id'] == row['opportunity_id']]
                            for _, item in items_in_opp.iterrows():
                                sol_name = item.get('solution', 'Unknown Solution')
                                item_cost = item.get('cost', 0)
                                st.markdown(f"<span style='font-size:13px;'>• {sol_name}: Rp {format_number(item_cost)}</span>", unsafe_allow_html=True)
                            
                            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                            # --------------------------------------------------------
                            
                            st.markdown(f"**💰 Total: Rp {format_number(row['cost'])}**")
                            
                            if st.button("View Detail", key=f"btn_{row['opportunity_id']}"):
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
            # 🧹 PRE-PROCESSING DATA
            # =================================================================
            
            # 1. Konversi Angka
            if 'cost' in df.columns:
                df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0)
            
            # 2. Konversi Tanggal & SORTING AWAL (PENTING!)
            date_col = 'start_date' if 'start_date' in df.columns else 'created_at'
            if date_col in df.columns:
                df['start_date_dt'] = pd.to_datetime(df[date_col], errors='coerce')
                # Sortir Default: Terbaru paling atas (Descending)
                df = df.sort_values(by='start_date_dt', ascending=False)
            
            # 3. Isi nilai kosong dengan string "Unknown"
            fillna_cols = [
                'presales_name', 'responsible_name', 'channel', 'brand', 'stage', 
                'salesgroup_id', 'pillar', 'solution', 'company_name', 
                'vertical_industry', 'opportunity_name', 'distributor_name', 'sales_name'
            ]
            for col in fillna_cols:
                if col in df.columns:
                    df[col] = df[col].fillna("Unknown").astype(str)

            # =================================================================
            # 🎛️ FILTER PANEL (SLICERS)
            # =================================================================
            with st.container(border=True):
                
                def get_opts(col_name):
                    return sorted(df[col_name].unique()) if col_name in df.columns else []

                # --- PINDAHKAN LOGIKA TANGGAL KE SINI ---
                # Agar bisa dibaca oleh fungsi reset di bawahnya
                min_date = df['start_date_dt'].min().date() if 'start_date_dt' in df.columns and not df['start_date_dt'].isnull().all() else None
                max_date = df['start_date_dt'].max().date() if 'start_date_dt' in df.columns and not df['start_date_dt'].isnull().all() else None

                # --- HEADER & CLEAR BUTTON ---
                col_title, col_btn = st.columns([0.85, 0.15])
                with col_title:
                    st.subheader("🔍 Filter Panel (Slicers)")
                with col_btn:
                    # Fungsi Callback untuk menghapus state filter secara EKSPLISIT
                    def reset_filters():
                        multiselect_keys = [
                            'f_inputter', 'f_pam', 'f_group', 'f_sales', 'f_channel', 'f_dist',
                            'f_brand', 'f_pillar', 'f_sol', 'f_client', 'f_vert', 'f_stage', 'f_opp'
                        ]
                        
                        # Timpa value dengan array kosong (ini memaksa UI di browser untuk bersih)
                        for key in multiselect_keys:
                            if key in st.session_state:
                                st.session_state[key] = []
                        
                        # Kembalikan kalender ke range default (min & max)
                        if 'f_date' in st.session_state:
                            st.session_state['f_date'] = (min_date, max_date) if min_date and max_date else None
                    
                    st.button("🧹 Clear All Filters", on_click=reset_filters, use_container_width=True)

                # --- Baris 1: Personil & Group ---
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                with c1: sel_inputter = st.multiselect("Inputter", get_opts('presales_name'), placeholder="All Inputters", key="f_inputter")
                with c2: sel_pam = st.multiselect("PAM", get_opts('responsible_name'), placeholder="All PAMs", key="f_pam")
                with c3: sel_group = st.multiselect("Sales Group", get_opts('salesgroup_id'), placeholder="All Groups", key="f_group")
                with c4: sel_sales = st.multiselect("Sales Name", get_opts('sales_name'), placeholder="All Sales", key="f_sales")
                with c5: sel_channel = st.multiselect("Channel", get_opts('channel'), placeholder="All Channels", key="f_channel")
                with c6: sel_distributor = st.multiselect("Distributor", get_opts('distributor_name'), placeholder="All Dist.", key="f_dist")

                # --- Baris 2: Produk & Client ---
                c7, c8, c9, c10, c11 = st.columns(5)
                with c7: sel_brand = st.multiselect("Brand", get_opts('brand'), placeholder="All Brands", key="f_brand")
                with c8: sel_pillar = st.multiselect("Pillar", get_opts('pillar'), placeholder="All Pillars", key="f_pillar")
                with c9: sel_solution = st.multiselect("Solution", get_opts('solution'), placeholder="All Solutions", key="f_sol")
                with c10: sel_client = st.multiselect("Client", get_opts('company_name'), placeholder="All Clients", key="f_client")
                with c11: sel_vertical = st.multiselect("Vertical", get_opts('vertical_industry'), placeholder="All Verticals", key="f_vert")

                # --- Baris 3: Stage, Date, Opportunity Name ---
                c12, c13, c14 = st.columns([1, 2, 3])
                with c12: 
                    sel_stage = st.multiselect("Stage", get_opts('stage'), placeholder="All Stages", key="f_stage")
                
                with c13:
                    # 1. Inisialisasi default ke dalam Session State (hanya jika belum ada)
                    if 'f_date' not in st.session_state:
                        st.session_state['f_date'] = (min_date, max_date) if min_date and max_date else None
                    
                    # 2. Render Widget TANPA parameter value=
                    date_range = st.date_input(
                        "Start Date Range",
                        help="Filter berdasarkan rentang tanggal Start Date",
                        key="f_date" # Parameter 'value' dihapus karena sudah di-handle oleh key ini
                    )
                
                with c14:
                    sel_opportunity = st.multiselect(
                        "Opportunity Name", 
                        get_opts('opportunity_name'), 
                        placeholder="Select Opportunity Name...",
                        key="f_opp"
                    )
                    
            # =================================================================
            # 🔄 LOGIKA FILTERING (ENGINE)
            # =================================================================
            df_filtered = df.copy()

            if sel_inputter: df_filtered = df_filtered[df_filtered['presales_name'].isin(sel_inputter)]
            if sel_pam: df_filtered = df_filtered[df_filtered['responsible_name'].isin(sel_pam)]
            if sel_group: df_filtered = df_filtered[df_filtered['salesgroup_id'].isin(sel_group)]
            if sel_sales: df_filtered = df_filtered[df_filtered['sales_name'].isin(sel_sales)]
            if sel_channel: df_filtered = df_filtered[df_filtered['channel'].isin(sel_channel)]
            if sel_distributor: df_filtered = df_filtered[df_filtered['distributor_name'].isin(sel_distributor)]
            if sel_brand: df_filtered = df_filtered[df_filtered['brand'].isin(sel_brand)]
            if sel_pillar: df_filtered = df_filtered[df_filtered['pillar'].isin(sel_pillar)]
            if sel_solution: df_filtered = df_filtered[df_filtered['solution'].isin(sel_solution)]
            if sel_client: df_filtered = df_filtered[df_filtered['company_name'].isin(sel_client)]
            if sel_vertical: df_filtered = df_filtered[df_filtered['vertical_industry'].isin(sel_vertical)]
            if sel_stage: df_filtered = df_filtered[df_filtered['stage'].isin(sel_stage)]
            
            if sel_opportunity:
                df_filtered = df_filtered[df_filtered['opportunity_name'].isin(sel_opportunity)]
            
            if isinstance(date_range, tuple) and len(date_range) == 2 and 'start_date_dt' in df.columns:
                start_d, end_d = date_range
                mask = (df_filtered['start_date_dt'].dt.date >= start_d) & (df_filtered['start_date_dt'].dt.date <= end_d)
                df_filtered = df_filtered[mask]

            # =================================================================
            # 📊 KPI CARDS
            # =================================================================
            st.markdown("### Summary")
            
            total_opps_lines = len(df_filtered)
            total_unique_opps = df_filtered['opportunity_id'].nunique() if 'opportunity_id' in df_filtered.columns else 0
            total_unique_customers = df_filtered['company_name'].nunique() if 'company_name' in df_filtered.columns else 0
            # KPI Total Value (Optional jika ingin diaktifkan)
            total_value = df_filtered['cost'].sum() if 'cost' in df_filtered.columns else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Solution Lines", f"{total_opps_lines}")
            m2.metric("Unique Opportunities", f"{total_unique_opps}")
            m3.metric("Unique Customers", f"{total_unique_customers}")

            st.markdown("---")

            # =================================================================
            # 📋 DATA TABLE (FIX SORTING)
            # =================================================================
            st.subheader(f"Detailed Data ({total_opps_lines} rows)")
            
            if not df_filtered.empty:
                # 1. Bersihkan data untuk display (Format angka, dll)
                display_df = clean_data_for_display(df_filtered)
                
                # 2. FIX UTAMA: Timpa kolom 'start_date' dengan objek datetime asli
                # Ini memaksa Streamlit menganggapnya sebagai Tanggal (bukan String)
                if 'start_date_dt' in df_filtered.columns and 'start_date' in display_df.columns:
                    display_df['start_date'] = df_filtered['start_date_dt']

                # 3. Render dengan Column Config
                st.dataframe(
                    display_df, 
                    use_container_width=True,
                    column_config={
                        # Format Date agar tampil "DD-MM-YYYY" tapi sorting tetap kalender
                        "start_date": st.column_config.DateColumn(
                            "Start Date",
                            format="DD-MM-YYYY"
                        ),
                        # (Opsional) Format Cost biar rapi
                        "cost": st.column_config.NumberColumn(
                            "Cost (IDR)",
                            format="Rp %.0f"
                        )
                    }
                )
            else:
                st.warning("Tidak ada data yang cocok dengan kombinasi filter di atas.")

@st.fragment
def tab4():
    st.header("Edit and Update Opportunity")
    st.info("💡 Pilih Opportunity dan Product Line. Anda dapat mengubah harga, notes, maupun detail lainnya sekaligus.")
    st.warning("⚠️ Perhatian: Mengubah Sales Group akan men-generate UID baru.")

    # --- HELPER: RESET STATE ---
    def reset_edit_state():
        st.session_state.lead_to_edit = None
        st.session_state.edit_submission_message = None
        st.session_state.edit_new_uid = None

    # --- HELPER: SAFE INDEX FINDER ---
    def get_index(data_list, value, key=None):
        try:
            if not data_list or value is None: return None
            if key: 
                vals = [str(item.get(key, "")).strip() for item in data_list]
                value = str(value).strip()
                return vals.index(value)
            return data_list.index(value)
        except (ValueError, TypeError, IndexError): 
            return None

    # 1. Inisialisasi State
    if 'lead_to_edit' not in st.session_state: st.session_state.lead_to_edit = None
    if 'edit_submission_message' not in st.session_state: st.session_state.edit_submission_message = None
    if 'edit_new_uid' not in st.session_state: st.session_state.edit_new_uid = None

    current_user_name = st.session_state.get('presales_session', {}).get('username', 'Unknown')

    # --- SECTION A: SELECTOR ---
    with st.spinner("Loading your opportunities..."):
        raw_data = db.get_leads_by_group_logic(current_user_name)

    if raw_data and raw_data.get('status') == 200 and raw_data.get('data'):
        df = pd.DataFrame(raw_data['data'])
        
        # 1. Dropdown Opportunity
        opp_list = sorted(df['opportunity_name'].unique().tolist())
        sel_opp_name = st.selectbox(
            "1. Select Opportunity Name", 
            opp_list, 
            key="tab4_sel_opp_name", 
            placeholder="Choose opportunity...", 
            index=None,
            on_change=reset_edit_state
        )

        # 2. Dropdown Product (Cascading)
        if sel_opp_name:
            subset = df[df['opportunity_name'] == sel_opp_name]
            
            # Mapping Label -> UID
            item_map = {}
            for idx, row in subset.iterrows():
                pillar = row.get('pillar') or "NoPillar"
                brand = row.get('brand') or "NoBrand"
                sol = row.get('solution') or "NoSol"
                svc = row.get('service') or "-"
                cost = row.get('cost') or 0
                label = f"{pillar} - {sol} ({svc}) - {brand} | Est: Rp {format_number(cost)}"
                item_map[label] = row['uid']
            
            sel_product_label = st.selectbox(
                "2. Select Product/Solution Line", 
                list(item_map.keys()), 
                key="tab4_sel_prod_label",
                on_change=reset_edit_state
            )

            # Tombol Load Data
            if st.button("Edit This Item", type="primary"):
                target_uid = item_map[sel_product_label]
                
                # Ambil data fresh detail (menggunakan get_single_lead agar datanya lengkap)
                res = db.get_single_lead({"uid": target_uid}) 
                if res.get("status") == 200 and res.get("data"):
                    st.session_state.lead_to_edit = res['data'][0]
                    st.session_state.edit_submission_message = None
                    st.session_state.edit_new_uid = None
                else:
                    st.error("Error fetching detailed data.")
        else:
            if st.session_state.lead_to_edit:
                reset_edit_state()
                st.rerun()
    else:
        st.warning("No opportunities found for your group.")
        st.stop() 

    # --- SECTION B: NOTIFICATION AREA ---
    if st.session_state.edit_submission_message:
        st.success(st.session_state.edit_submission_message)
        if st.session_state.edit_new_uid:
            st.info(f"📢 **IMPORTANT:** UID Updated! New UID: `{st.session_state.edit_new_uid}`")
        if st.button("Close Message"):
            st.session_state.edit_submission_message = None
            st.rerun()

    # --- SECTION C: FULL EDIT FORM ---
    if st.session_state.lead_to_edit:
        lead = st.session_state.lead_to_edit
        
        st.markdown("---")
        st.subheader(f"Editing: {lead.get('opportunity_name', 'Unknown')}")
        st.caption(f"Current UID: `{lead.get('uid')}`")

        # Double Check Consistency
        if sel_opp_name and lead['opportunity_name'] != sel_opp_name:
             st.warning("⚠️ Data mismatch. Please select the item again.")
             st.session_state.lead_to_edit = None
             st.stop()

        # Load Master Data
        all_sales_groups = get_sales_groups()
        all_responsibles = get_master('getResponsibles')
        all_pillars = get_pillars()
        all_brands = get_master('getBrands')
        all_companies_data = get_master('getCompanies')
        all_distributors = get_master('getDistributors')

        # --- TABS UNTUK MEMBAGI KATEGORI FORM ---
        t_cost, t_sales, t_prod, t_cust = st.tabs(["💰 Cost & Notes", "👥 Sales Info", "📦 Product Solution", "🏢 Customer Info"])
        
        # ---------------------------------------------------------
        # TAB DALAM FORM 1: COST & NOTES (Ex-Tab 4)
        # ---------------------------------------------------------
        with t_cost:
            st.markdown("##### Update Cost & Margin")
            col_curr, col_val = st.columns([0.3, 0.7])
            with col_curr:
                currency = st.selectbox("Input Currency", ["IDR", "USD"], key="upd_currency")
            
            current_rate = get_usd_to_idr_rate()
            
            with col_val:
                default_val = float(lead.get('cost') or 0) if currency == "IDR" else 0.0
                input_val = st.number_input(
                    f"New Cost ({currency})", value=default_val, min_value=0.0, step=1000000.0 if currency=="IDR" else 100.0
                )

            # Logika Konversi & Cisco
            final_cost_idr = 0
            calc_info = ""

            if currency == "USD":
                brand_name = lead.get('brand', '').strip()
                if brand_name.lower() == "cisco":
                    discounted_usd = input_val * 0.6
                    final_cost_idr = discounted_usd * current_rate
                    calc_info = f"ℹ️ **Cisco Logic (50% Disc):** ${input_val:,.0f} x 0.5 x {current_rate} = Rp {format_number(final_cost_idr)}"
                else:
                    final_cost_idr = input_val * current_rate
                    calc_info = f"ℹ️ **Conversion:** ${input_val:,.0f} x {current_rate} = Rp {format_number(final_cost_idr)}"
                st.info(calc_info)
            else:
                final_cost_idr = input_val
                st.caption(f"Final Value stored: Rp {format_number(final_cost_idr)}")
            
            new_notes = st.text_area("Notes", value=lead.get('notes', ''))

        # ---------------------------------------------------------
        # TAB DALAM FORM 2: SALES INFO (Ex-Tab 5)
        # ---------------------------------------------------------
        with t_sales:
            st.markdown("##### Sales & Internal Info")
            edited_sales_group = st.selectbox("Sales Group", all_sales_groups, 
                index=get_index(all_sales_groups, lead.get('salesgroup_id')), key="edit_sg")
            
            sales_opts = get_sales_name_by_sales_group(edited_sales_group)
            edited_sales_name = st.selectbox("Sales Name", sales_opts, 
                index=get_index(sales_opts, lead.get('sales_name')), key="edit_sn")
            
            edited_responsible = st.selectbox("Presales Account Manager", all_responsibles, 
                index=get_index(all_responsibles, lead.get('responsible_name'), 'Responsible'), 
                format_func=lambda x: x.get("Responsible", "") if isinstance(x, dict) else str(x), key="edit_pam")

        # ---------------------------------------------------------
        # TAB DALAM FORM 3: PRODUCT SOLUTION (Ex-Tab 5)
        # ---------------------------------------------------------
        with t_prod:
            st.markdown("##### Product Solution")
            edited_pillar = st.selectbox("Pillar", all_pillars, 
                index=get_index(all_pillars, lead.get('pillar')), key="edit_pillar")
            
            solution_options = get_solutions(edited_pillar)
            edited_solution = st.selectbox("Solution", solution_options, 
                index=get_index(solution_options, lead.get('solution')), key="edit_sol")
            
            service_options = get_services(edited_solution)
            edited_service = st.selectbox("Service", service_options, 
                index=get_index(service_options, lead.get('service')), key="edit_svc")
            
            edited_brand = st.selectbox("Brand", all_brands, 
                index=get_index(all_brands, lead.get('brand'), 'Brand'), 
                format_func=lambda x: x.get("Brand", "") if isinstance(x, dict) else str(x), key="edit_brand")

        # ---------------------------------------------------------
        # TAB DALAM FORM 4: CUSTOMER INFO (Ex-Tab 5)
        # ---------------------------------------------------------
        with t_cust:
            st.markdown("##### Customer Info & Distributor")
            edited_company = st.selectbox("Company", all_companies_data, 
                index=get_index(all_companies_data, lead.get('company_name'), 'Company'), 
                format_func=lambda x: x.get("Company", "") if isinstance(x, dict) else str(x), key="edit_comp")
            
            derived_vertical = edited_company.get('Vertical Industry', '') if isinstance(edited_company, dict) else lead.get('vertical_industry', '')
            st.text_input("Vertical Industry (Auto)", value=derived_vertical, disabled=True, key="edit_vert")

            current_dist = lead.get('distributor_name', 'Not via distributor')
            is_via_default = 0 if current_dist != "Not via distributor" and current_dist else 1
            is_via = st.radio("Via Distributor?", ("Yes", "No"), index=is_via_default, horizontal=True, key="edit_via")
            
            final_dist = "Not via distributor"
            if is_via == "Yes":
                edited_dist = st.selectbox("Select Distributor", all_distributors, 
                    index=get_index(all_distributors, current_dist, 'Distributor'), 
                    format_func=lambda x: x.get("Distributor", "") if isinstance(x, dict) else str(x), key="edit_dist_name")
                final_dist = edited_dist.get('Distributor') if isinstance(edited_dist, dict) else edited_dist

        # --- SAVE ACTION ---
        st.markdown("---")
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            with st.spinner("Saving changes to database..."):
                # 1. Update Cost & Notes (Ex-Tab 4 logic)
                res_cost = db.update_lead({
                    "uid": lead['uid'], 
                    "cost": final_cost_idr, 
                    "notes": new_notes, 
                    "user": current_user_name 
                })

                # Persiapan variabel Final Brand untuk payload dan email
                final_brand_str = edited_brand.get('Brand') if isinstance(edited_brand, dict) else edited_brand

                # 2. Update Header Detail (Ex-Tab 5 logic)
                payload = lead.copy()
                payload.update({
                    "salesgroup_id": edited_sales_group,
                    "sales_name": edited_sales_name,
                    "responsible_name": edited_responsible.get('Responsible') if isinstance(edited_responsible, dict) else edited_responsible,
                    "pillar": edited_pillar,
                    "solution": edited_solution,
                    "service": edited_service,
                    "brand": final_brand_str,
                    "company_name": edited_company.get('Company') if isinstance(edited_company, dict) else edited_company,
                    "vertical_industry": derived_vertical,
                    "distributor_name": final_dist,
                    "user": current_user_name
                })
                res_full = db.update_full_opportunity(payload)
                
                # Evaluasi Hasil
                if res_cost['status'] == 200 and res_full['status'] == 200:
                    st.session_state.edit_submission_message = "✅ Data (Cost & Full Details) Updated Successfully!"
                    
                    # ==========================================================
                    # --- LOGIKA BARU: AUTO-NOTIFIKASI EMAIL KE CHANNEL PIC ---
                    # ==========================================================
                    try:
                        # a. Ambil email map dari data Presales
                        presales_data = get_master('getPresales') 
                        email_map = {p['PresalesName']: p['Email'] for p in presales_data if p.get('Email')}
                        
                        # b. Cari siapa nama Channel PIC untuk brand yang baru saja di-save
                        pic_name = None
                        for b in all_brands:
                            # Mengakomodir nama key dari Master DB (Brand/brand_name)
                            b_name = b.get('Brand') or b.get('brand_name') 
                            if b_name == final_brand_str:
                                pic_name = b.get('Channel') or b.get('channel')
                                break
                        
                        # c. Jika ada PIC-nya dan email-nya terdaftar, kirim email notifikasi
                        if pic_name and pic_name in email_map:
                            target_email = email_map[pic_name]
                            
                            # Format rincian produk yang di-update
                            sol_details = f"<li><b>{payload['solution']}</b> ({final_brand_str}) - Rp {format_number(final_cost_idr)}</li>"
                            notes_html = f"<p><b>Latest Notes:</b> {new_notes}</p>" if new_notes else ""
                            
                            email_body = f"""
                            <h3>🔄 Opportunity Updated</h3>
                            <p>Halo {pic_name}, terdapat perubahan data pada Opportunity berikut:</p>
                            <p>
                                <b>Opportunity:</b> {payload['opportunity_name']}<br>
                                <b>Customer:</b> {payload['company_name']}<br>
                                <b>Sales:</b> {payload['sales_name']} ({payload['salesgroup_id']})<br>
                                <b>Updated By:</b> {current_user_name}
                            </p>
                            <hr>
                            <p><b>Updated Solution Details:</b></p>
                            <ul>{sol_details}</ul>
                            {notes_html}
                            <p style='font-size: 10px; color: grey;'>Generated by Presales App - Edit Module</p>
                            """
                            
                            db.send_email_background(
                                target_email, 
                                f"[Update Opp] {payload['opportunity_name']}", 
                                email_body
                            )
                            st.toast(f"📧 Update notification sent to {pic_name} ({target_email})", icon="✅")
                    except Exception as e:
                        st.toast(f"⚠️ Data saved but email notification failed: {e}", icon="⚠️")
                    # ==========================================================

                    # Cek UID Change
                    new_uid_db = res_full.get("data", {}).get("uid")
                    if new_uid_db and new_uid_db != lead.get('uid'):
                        st.session_state.edit_new_uid = new_uid_db
                    
                    st.session_state.lead_to_edit = None 
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(f"Failed to update some data. Cost msg: {res_cost['message']} | Detail msg: {res_full['message']}")

@st.fragment
def tab5():
    st.header("Update Opportunity Stage")
    st.info("Pilih Opportunity untuk mengubah status (Stage) ke seluruh baris produk sekaligus.")

    # 1. Cek Session
    if 'presales_session' in st.session_state:
        current_user = st.session_state.presales_session['username']
    else:
        st.error("Session missing.")
        return

    # 2. Ambil data
    with st.spinner("Loading opportunities..."):
        raw_data = db.get_leads_by_group_logic(current_user)
    
    if raw_data and raw_data.get('status') == 200 and raw_data.get('data'):
        df = pd.DataFrame(raw_data['data'])
        
        # Buat dictionary unik: Opportunity Name -> ID & Stage saat ini
        # Karena kita hanya butuh level Parent/Header
        opp_dict = {}
        for _, row in df.iterrows():
            opp_name = row['opportunity_name']
            if opp_name not in opp_dict:
                opp_dict[opp_name] = {
                    "id": row['opportunity_id'],
                    "stage": row.get('stage', 'Open')
                }

        opp_list = sorted(list(opp_dict.keys()))
        sel_opp_name = st.selectbox(
            "1. Select Opportunity", 
            opp_list, 
            index=None, 
            placeholder="Choose opportunity to update..."
        )

        # 3. Form Update
        if sel_opp_name:
            opp_info = opp_dict[sel_opp_name]
            opp_id = opp_info["id"]
            curr_stage = opp_info["stage"]

            st.markdown("---")
            st.write(f"**Current Stage:** `{curr_stage}`")

            # Opsi Stage Standar
            stage_options = ["Open", "Closed Won", "Closed Lost"]
            
            # Cari index default sesuai stage saat ini
            try:
                default_idx = stage_options.index(curr_stage)
            except ValueError:
                default_idx = 0

            new_stage = st.selectbox("2. Select New Stage", stage_options, index=default_idx)

            if st.button("💾 Update Stage", type="primary"):
                if new_stage == curr_stage:
                    st.warning("⚠️ Stage tidak ada perubahan.")
                else:
                    with st.spinner("Updating stage to all related products..."):
                        res = db.update_opportunity_stage(opp_id, new_stage, current_user)
                        
                        if res['status'] == 200:
                            st.success(f"✅ {res['message']}")
                            
                            # ==========================================================
                            # --- LOGIKA BARU: AUTO-NOTIFIKASI STAGE KE CHANNEL PIC ---
                            # ==========================================================
                            try:
                                # 1. Filter baris data khusus untuk Opportunity yang dipilih
                                opp_lines = df[df['opportunity_name'] == sel_opp_name]
                                involved_brands = opp_lines['brand'].dropna().unique().tolist()
                                
                                # Ambil detail header (dari baris pertama) untuk isi email
                                first_row = opp_lines.iloc[0]
                                customer_name = first_row.get('company_name', 'Unknown')
                                sales_name = first_row.get('sales_name', 'Unknown')
                                sales_group = first_row.get('salesgroup_id', 'Unknown')

                                # 2. Load Master Data
                                all_brands = get_master('getBrands')
                                presales_data = get_master('getPresales')
                                email_map = {p['PresalesName']: p['Email'] for p in presales_data if p.get('Email')}

                                # 3. Kumpulkan email PIC terkait
                                target_emails = set()
                                for brand in involved_brands:
                                    for b in all_brands:
                                        b_name = b.get('Brand') or b.get('brand_name')
                                        if b_name == brand:
                                            pic_name = b.get('Channel') or b.get('channel')
                                            if pic_name and pic_name in email_map:
                                                target_emails.add(email_map[pic_name])
                                            break
                                
                                # 4. Jika ada PIC, kirim blast email
                                if target_emails:
                                    target_email_string = ", ".join(target_emails)
                                    
                                    # Rangkai daftar solusi untuk di badan email
                                    sol_html = "<ul>"
                                    for _, row in opp_lines.iterrows():
                                        sol = row.get('solution', 'No Solution')
                                        brnd = row.get('brand', 'No Brand')
                                        cst = row.get('cost', 0)
                                        sol_html += f"<li><b>{sol}</b> ({brnd}) - Rp {format_number(cst)}</li>"
                                    sol_html += "</ul>"
                                    
                                    # Warna teks dinamis tergantung status
                                    color = "green" if new_stage == "Closed Won" else "red" if new_stage == "Closed Lost" else "blue"

                                    email_body = f"""
                                    <h3>📢 Opportunity Stage Updated</h3>
                                    <p>Status Opportunity berikut telah diubah menjadi <b><span style='color: {color};'>{new_stage}</span></b>.</p>
                                    <p>
                                        <b>Opportunity:</b> {sel_opp_name}<br>
                                        <b>Customer:</b> {customer_name}<br>
                                        <b>Sales:</b> {sales_name} ({sales_group})<br>
                                        <b>Updated By:</b> {current_user}
                                    </p>
                                    <hr>
                                    <p><b>Solution Details:</b></p>
                                    {sol_html}
                                    <p style='font-size: 10px; color: grey;'>Generated by Presales App - Update Stage Module</p>
                                    """
                                    
                                    db.send_email_background(
                                        target_email_string, 
                                        f"[{new_stage}] {sel_opp_name}", 
                                        email_body
                                    )
                                    st.toast(f"📧 Stage update notification sent to Channel PICs!", icon="✅")
                            except Exception as e:
                                st.toast(f"⚠️ Stage updated but email notification failed: {e}", icon="⚠️")
                            # ==========================================================

                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(f"Failed: {res['message']}")
    else:
        st.warning("No opportunities found for your group.")

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