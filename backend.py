from logger_setup import logger
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import time
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==============================================================================
# 1. KONEKSI DATABASE
# ==============================================================================

def get_db_engine():
    """
    Membuat Engine Database dengan cara AMAN (Lewat Secrets).
    """
    print("🕵️ DEBUG: Memulai inisialisasi Database Engine...")
    
    # 1. Cek apakah secrets terdeteksi
    if "connections" not in st.secrets:
        st.error("❌ ERROR: File '.streamlit/secrets.toml' tidak ditemukan atau format salah.")
        print("❌ ERROR: Secrets tidak ditemukan.")
        st.stop()

    try:
        # 2. Ambil config
        db_conf = st.secrets["connections"]["postgresql"]
        print("✅ DEBUG: Secrets ditemukan. Mencoba menyusun URL...")
        
        # 3. Validasi isi secrets
        required_keys = ["username", "password", "host", "port", "database"]
        missing_keys = [k for k in required_keys if k not in db_conf]
        
        if missing_keys:
            st.error(f"❌ ERROR: Konfigurasi secrets kurang lengkap. Hilang: {missing_keys}")
            st.stop()

        # 4. Construct URL
        # Format: postgresql+psycopg2://user:pass@host:port/dbname
        db_url = f"postgresql+psycopg2://{db_conf['username']}:{db_conf['password']}@{db_conf['host']}:{db_conf['port']}/{db_conf['database']}"
        
        print(f"🔌 DEBUG: URL Database terbentuk (Host: {db_conf['host']}). Mencoba create_engine...")

        engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=10,      
            pool_recycle=1800,
            pool_pre_ping=True
        )
        
        print("🚀 DEBUG: Engine berhasil dibuat!")
        return engine

    except Exception as e:
        clean_error = str(e).split("@")[-1]
        st.error(f"❌ Critical Error Database: ...@{clean_error}")
        print(f"❌ Critical Error: {str(e)}")
        st.stop()

# Inisialisasi Engine Global
engine = get_db_engine()

def get_now_jakarta():
    """Helper untuk mendapatkan waktu Jakarta (WIB) tanpa library pytz."""
    return datetime.utcnow() + timedelta(hours=7)

# ==============================================================================
# SECTION 0: AUTHENTICATION (PRESALES)
# ==============================================================================

def validate_presales_login(username, password):
    query = text("SELECT presales_name, email, need_password_change, access_group FROM presales WHERE presales_name = :u AND password = :p")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"u": username, "p": password})
            row = result.mappings().fetchone()
            
            if row:
                return {
                    "status": 200, 
                    "data": {
                        "username": row['presales_name'],
                        "email": row['email'],
                        "access_group": row['access_group'],
                        "need_password_change": bool(row['need_password_change']) 
                    }
                }
            else:
                return {"status": 401, "message": "Nama atau Password salah."}
            
    except Exception as e:
        return {"status": 500, "message": str(e)}

def change_user_password(username, new_password):
    try:
        with engine.begin() as conn:
            query = text("""
                UPDATE presales 
                SET password = :np, need_password_change = FALSE 
                WHERE presales_name = :u
            """)
            conn.execute(query, {"np": new_password, "u": username})
            return {"status": 200, "message": "Password berhasil diubah!"}
    except Exception as e:
        return {"status": 500, "message": str(e)}

def get_presales_users_list():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT presales_name FROM presales ORDER BY presales_name"))
            return [row[0] for row in result.fetchall()]
    except:
        return []

# ==============================================================================
# SECTION 1: EMAIL UTILITIES
# ==============================================================================

def send_email_notification(recipient_email, subject, body_html):
    try:
        SMTP_SERVER = st.secrets["smtp"]["server"]
        SMTP_PORT = int(st.secrets["smtp"]["port"])
        SENDER_EMAIL = st.secrets["smtp"]["email"]
        SENDER_PASSWORD = st.secrets["smtp"]["password"]
    except Exception as e:
        return {"status": 500, "message": "Konfigurasi SMTP tidak ditemukan di secrets.toml"}

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return {"status": 200, "message": "Email sent successfully"}
    except Exception as e:
        return {"status": 500, "message": f"Email failed: {str(e)}"}

# ==============================================================================
# SECTION 2: READ OPERATIONS (GET)
# ==============================================================================

def get_master_presales(action):
    queries = {
        "getPresales": "SELECT presales_name as \"PresalesName\", email as \"Email\" FROM presales ORDER BY presales_name",
        "getPAMMapping": "SELECT inputter_name as \"Inputter\", pam_name as \"PAM\" FROM mapping_pam",
        "getBrands": "SELECT brand_name as \"Brand\", channel as \"Channel\" FROM brands WHERE brand_name IS NOT NULL ORDER BY brand_name, channel",
        "getPillars": "SELECT DISTINCT pillar_name as \"Pillar\", solution_name as \"Solution\", service_name as \"Service\" FROM master_pillars ORDER BY pillar_name, solution_name, service_name",
        "getPresalesStages": "SELECT stage_name as \"Stage\" FROM stage_pipeline WHERE stage_type = 'PRESALES' ORDER BY stage_name",
        "getSalesGroups": "SELECT DISTINCT sales_group as \"SalesGroup\" FROM sales_names ORDER BY sales_group",
        "getSalesNames": "SELECT sales_group as \"SalesGroup\", sales_name as \"SalesName\" FROM sales_names ORDER BY sales_name",
        "getResponsibles": "SELECT DISTINCT responsible_name as \"Responsible\" FROM responsible WHERE responsible_name IS NOT NULL",
        "getCompanies": "SELECT DISTINCT company_name as \"Company\", vertical_industry as \"Vertical Industry\" FROM companies ORDER BY company_name",
        "getDistributors": "SELECT DISTINCT distributor_name as \"Distributor\" FROM distributors WHERE distributor_name IS NOT NULL ORDER BY distributor_name",
        "getOpportunities": "SELECT DISTINCT opportunity_name as \"Desc\" FROM opportunities ORDER BY opportunity_name",
        "getActivityLog": "SELECT timestamp as \"Timestamp\", opportunity_name as \"OpportunityName\", user_name as \"User\", action as \"Action\", field as \"Field\", old_value as \"OldValue\", new_value as \"NewValue\" FROM activity_logs ORDER BY timestamp DESC LIMIT 1000"
    }
    
    if action in queries:
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(queries[action]), conn)
                return df.to_dict('records')
        except Exception as e:
            st.error(f"DB Error ({action}): {e}")
            return []
    return []

def get_leads_by_group_logic(username):
    try:
        with engine.connect() as conn:
            # 1. Cek Grup User
            check = conn.execute(text("SELECT access_group FROM presales WHERE presales_name = :u"), {"u": username}).mappings().first()
            
            if not check:
                return {"status": 404, "data": []}
                
            user_group = check['access_group']
            
            # --- LOGIKA: SUPER USER / TOP MGMT ---
            if user_group == 'TOP_MGMT':
                query = text("SELECT * FROM opportunities ORDER BY created_at DESC")
                df = pd.read_sql(query, conn)
                return {"status": 200, "data": df.to_dict('records')}
            
            # --- LOGIKA: USER BIASA & SPESIALIS ---
            query = text("""
                SELECT o.* FROM opportunities o
                LEFT JOIN presales p ON o.presales_name = p.presales_name
                WHERE 
                    p.access_group = :ug
                    OR ( :ug = 'DC_TEAM'  AND o.pillar = 'Data Center' )
                    OR ( :ug = 'SEC_TEAM' AND o.pillar = 'Cyber Security' )
                    OR ( :ug = 'MS_TEAM'  AND o.pillar = 'Maintenance Services' )
                ORDER BY o.created_at DESC
            """)
            
            df = pd.read_sql(query, conn, params={"ug": user_group})
            return {"status": 200, "data": df.to_dict('records')}
            
    except Exception as e:
        return {"status": 500, "message": str(e), "data": []}

def get_single_lead(search_params):
    if "uid" in search_params:
        try:
            with engine.connect() as conn:
                query = text("SELECT * FROM opportunities WHERE uid = :uid")
                df = pd.read_sql(query, conn, params={"uid": search_params["uid"]})
                if not df.empty:
                    return {"status": 200, "data": df.to_dict('records')}
        except Exception as e:
            return {"status": 500, "message": str(e)}
    return {"status": 404, "message": "Not Found"}

def get_lead_by_uid(uid):
    """Mengambil data spesifik berdasarkan UID string."""
    try:
        with engine.connect() as conn:
            query = text("SELECT * FROM opportunities WHERE uid = :uid")
            df = pd.read_sql(query, conn, params={"uid": uid})
            if not df.empty:
                return {"status": 200, "data": df.to_dict('records')}
            else:
                return {"status": 404, "message": "UID Not Found"}
    except Exception as e:
        return {"status": 500, "message": str(e)}

def get_opportunity_summary(opp_id):
    """Mengambil ringkasan opportunity berdasarkan ID untuk preview."""
    try:
        with engine.connect() as conn:
            query_str = text("""
                SELECT opportunity_name, company_name, stage, COUNT(uid) as total_items 
                FROM opportunities 
                WHERE opportunity_id = :oid 
                GROUP BY opportunity_name, company_name, stage
            """)
            df = pd.read_sql(query_str, conn, params={"oid": opp_id})
            
            if not df.empty:
                return {"status": 200, "data": df.iloc[0].to_dict()}
            else:
                return {"status": 404, "message": "Opportunity ID not found"}
    except Exception as e:
        return {"status": 500, "message": str(e)}

def get_activity_log_by_group(username):
    """Mengambil Log Aktivitas berdasarkan Access Group User."""
    try:
        with engine.connect() as conn:
            check = conn.execute(text("SELECT access_group FROM presales WHERE presales_name = :u"), {"u": username}).mappings().first()
            if not check: return []
            user_group = check['access_group']
            
            if user_group == 'TOP_MGMT':
                query = text("""
                    SELECT 
                        l.timestamp as "Timestamp", l.opportunity_name as "OpportunityName", 
                        l.user_name as "user_name", l.action as "Action", 
                        l.field as "Field", l.old_value as "OldValue", l.new_value as "NewValue" 
                    FROM activity_logs l ORDER BY l.timestamp DESC LIMIT 1000
                """)
                df = pd.read_sql(query, conn)
            else:
                query = text("""
                    SELECT 
                        l.timestamp as "Timestamp", l.opportunity_name as "OpportunityName", 
                        l.user_name as "user_name", l.action as "Action", 
                        l.field as "Field", l.old_value as "OldValue", l.new_value as "NewValue" 
                    FROM activity_logs l
                    JOIN presales p ON l.user_name = p.presales_name
                    WHERE p.access_group = :ug
                    ORDER BY l.timestamp DESC LIMIT 1000
                """)
                df = pd.read_sql(query, conn, params={"ug": user_group})
            
            return df.to_dict('records')
            
    except Exception as e:
        logger.error(f"Log Error: {e}")
        return []

# ==============================================================================
# SECTION 3: WRITE OPERATIONS (INPUT & UPDATE)
# ==============================================================================

def add_multi_line_opportunity(parent_data, product_lines):
    try:
        with engine.begin() as conn:
            # A. Logic Rows ID (Q3xxxx)
            chk_q = text("SELECT rows_id FROM description WHERE description = :desc LIMIT 1")
            res_desc = conn.execute(chk_q, {"desc": parent_data['opportunity_name']}).mappings().first()
            
            if res_desc:
                current_rows_id = res_desc['rows_id']
            else:
                # Generate New Q1 ID
                max_q = text("SELECT MAX(rows_id) FROM description WHERE rows_id LIKE 'Q1%' AND LENGTH(rows_id) = 6")
                max_val = conn.execute(max_q).scalar()
                
                new_seq = 1
                if max_val:
                    try: new_seq = int(max_val[2:]) + 1
                    except: pass
                
                current_rows_id = f"Q1{str(new_seq).zfill(4)}"
                
                # Insert Deskripsi Baru
                conn.execute(text("INSERT INTO description (rows_id, description) VALUES (:rid, :desc)"), 
                             {"rid": current_rows_id, "desc": parent_data['opportunity_name']})
            
            # B. Generate Opp ID
            safe_group = parent_data.get('salesgroup_id', 'GEN')
            new_opp_id = f"{safe_group}{current_rows_id}"
            created_at = get_now_jakarta()
            created_uids = []
            
            # --- [SYNC] INSERT KE HEADER SALES (Integrasi Sales App) ---
            check_header = text("SELECT opportunity_id FROM sales_opportunities WHERE opportunity_id = :oid")
            if not conn.execute(check_header, {"oid": new_opp_id}).first():
                ins_header = text("""
                    INSERT INTO sales_opportunities (
                        opportunity_id, opportunity_name, salesgroup_id, sales_name, 
                        stage, created_at, updated_at
                    ) VALUES (
                        :oid, :oname, :sgid, :sname, 
                        :stg, :now, :now
                    )
                """)
                conn.execute(ins_header, {
                    "oid": new_opp_id,
                    "oname": parent_data['opportunity_name'],
                    "sgid": parent_data['salesgroup_id'],
                    "sname": parent_data['sales_name'],
                    "stg": parent_data.get('stage', 'Open'),
                    "now": created_at
                })
            
            # Loop setiap item
            for line in product_lines:
                # Lookup Product ID Components
                cat_q = text("SELECT pillar_id, solution_id, service_id FROM master_pillars WHERE pillar_name=:p AND solution_name=:s AND service_name=:svc LIMIT 1")
                cat = conn.execute(cat_q, {"p": line['pillar'], "s": line['solution'], "svc": line['service']}).mappings().first()
                
                br_q = text("SELECT brand_id FROM brands WHERE brand_name=:b LIMIT 1")
                br = conn.execute(br_q, {"b": line.get('brand')}).mappings().first()
                
                pid = cat['pillar_id'] if cat else "GEN"
                sol = str(cat['solution_id']) if cat else "0"
                svc = str(cat['service_id']) if cat else "S0"
                br_code = br['brand_id'] if br else "GEN"
                
                product_id_code = f"{pid}{sol}{svc}{br_code}".replace(" ", "").upper()
                unique_ts = time.time_ns()
                uid = f"{new_opp_id}-{product_id_code}-{unique_ts}"
                
                # Insert Detail
                ins_opp = text("""
                    INSERT INTO opportunities (
                        uid, opportunity_id, product_id, presales_name, salesgroup_id, sales_name, 
                        responsible_name, opportunity_name, start_date, company_name, 
                        vertical_industry, pillar, solution, service, 
                        pillar_product, solution_product, 
                        brand, channel, distributor_name, cost, notes, stage, created_at, updated_at
                    ) VALUES (
                        :uid, :oid, :pid, :pname, :sgid, :sname, 
                        :pam, :oname, :sdate, :cname, 
                        :vi, :plr, :sol, :svc, 
                        :pp, :sp, 
                        :br, :ch, :dist, :cost, :note, :stage_val, :now, :now
                    )
                """)
                
                conn.execute(ins_opp, {
                    "uid": uid, "oid": new_opp_id, "pid": product_id_code,
                    "pname": parent_data['presales_name'], "sgid": parent_data['salesgroup_id'], 
                    "sname": parent_data['sales_name'], "pam": parent_data['responsible_name'], 
                    "oname": parent_data['opportunity_name'], "sdate": parent_data['start_date'],
                    "cname": parent_data['company_name'], "vi": parent_data['vertical_industry'],
                    "plr": line['pillar'], "sol": line['solution'], "svc": line['service'],
                    "pp": line.get('pillar_product', None),
                    "sp": line.get('solution_product', None),
                    "br": line.get('brand'), "ch": line.get('channel'), "dist": line.get('distributor_name'), 
                    "cost": line.get('cost', 0), "note": line.get('notes', ''), 
                    "stage_val": parent_data.get('stage', 'Open'),
                    "now": created_at
                })
                
                created_uids.append({"uid": uid, "opportunity_id": new_opp_id})
            
            # Log Activity
            log_q = text("INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, new_value) VALUES (:ts, :oname, :user, 'CREATE', 'New Opportunity', :val)")
            conn.execute(log_q, {
                "ts": created_at, "oname": parent_data['opportunity_name'], 
                "user": parent_data['presales_name'], "val": f"Created {len(product_lines)} lines. ID: {new_opp_id}"
            })
            
            logger.info(f"SUCCESS: Opportunity '{parent_data['opportunity_name']}' created by {parent_data['presales_name']}")
            return {"status": 200, "message": "Opportunity successfully added!", "data": created_uids}
            
    except Exception as e:
        logger.error(f"CRITICAL ERROR in add_multi_line_opportunity: {str(e)}")
        return {"status": 500, "message": f"Database Error: {str(e)}"}

def update_lead(lead_data):
    try:
        with engine.begin() as conn:
            current_ts = get_now_jakarta()
            uid = lead_data['uid']
            user = lead_data['user']
            new_cost = lead_data['cost']
            new_notes = lead_data['notes']

            old = conn.execute(text("SELECT opportunity_name, cost, notes FROM opportunities WHERE uid=:u"), {"u": uid}).mappings().first()
            
            if not old: return {"status": 404, "message": "Data not found"}
            
            conn.execute(text("UPDATE opportunities SET cost=:c, notes=:n, updated_at=:ts WHERE uid=:u"), 
                         {"c": new_cost, "n": new_notes, "u": uid, "ts": current_ts})
            
            # --- LOGGING PERUBAHAN ---
            
            # 1. Cost
            old_cost_val = float(old['cost']) if old['cost'] is not None else 0.0
            new_cost_val = float(new_cost) if new_cost is not None else 0.0
            
            if abs(old_cost_val - new_cost_val) > 0.01:
                log = text("""
                    INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value) 
                    VALUES (:ts, :oname, :u, 'UPDATE', 'Cost', :ov, :nv)
                """)
                conn.execute(log, {
                    "ts": current_ts,
                    "oname": old['opportunity_name'],
                    "u": user, 
                    "ov": f"{old_cost_val:,.0f}", 
                    "nv": f"{new_cost_val:,.0f}"
                })

            # 2. Notes
            old_notes_val = str(old['notes']) if old['notes'] else ""
            new_notes_val = str(new_notes) if new_notes else ""
            
            if old_notes_val.strip() != new_notes_val.strip():
                log = text("""
                    INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value) 
                    VALUES (:ts, :oname, :u, 'UPDATE', 'Notes', :ov, :nv)
                """)
                conn.execute(log, {
                    "ts": current_ts,
                    "oname": old['opportunity_name'],
                    "u": user, 
                    "ov": old_notes_val, 
                    "nv": new_notes_val
                })

            return {"status": 200, "message": "Updated successfully"}
    except Exception as e:
        return {"status": 500, "message": str(e)}

def update_full_opportunity(payload):
    try:
        with engine.begin() as conn:
            # 1. Ambil Data Lama
            old_data = conn.execute(text("SELECT * FROM opportunities WHERE uid=:uid"), {"uid": payload['uid']}).mappings().first()
            if not old_data: return {"status": 404, "message": "UID not found"}
            
            # 2. GENERATE NEW OPP ID (Jika Sales Group berubah)
            rows_id_part = ""
            desc_res = conn.execute(text("SELECT rows_id FROM description WHERE description=:d"), {"d": old_data['opportunity_name']}).mappings().first()
            
            if desc_res:
                rows_id_part = desc_res['rows_id']
            else:
                match = re.search(r'(Q[1-4]\d+)', old_data['opportunity_id'])
                rows_id_part = match.group(1) if match else old_data['opportunity_id'][-6:]
            
            new_opp_id = f"{payload['salesgroup_id']}{rows_id_part}"
            
            # 3. GENERATE NEW PRODUCT ID CODE
            cat = conn.execute(text("SELECT pillar_id, solution_id, service_id FROM master_pillars WHERE pillar_name=:p AND solution_name=:s AND service_name=:svc LIMIT 1"),
                               {"p": payload['pillar'], "s": payload['solution'], "svc": payload['service']}).mappings().first()
            
            br = conn.execute(text("SELECT brand_id FROM brands WHERE brand_name=:b LIMIT 1"), {"b": payload['brand']}).mappings().first()
            
            pid = cat['pillar_id'] if cat else "GEN"
            sol = str(cat['solution_id']) if cat else "0"
            svc = str(cat['service_id']) if cat else "S0"
            br_code = br['brand_id'] if br else "GEN"
            
            new_product_id_code = f"{pid}{sol}{svc}{br_code}".replace(" ", "").upper()

            # 4. KONSTRUKSI UID BARU
            parts = old_data['uid'].split('-')
            ts_part = parts[-1]
            new_uid = f"{new_opp_id}-{new_product_id_code}-{ts_part}"
            
            # 5. EXECUTE UPDATE
            upd_q = text("""
                UPDATE opportunities SET
                    uid=:nuid, opportunity_id=:noid, product_id=:npid,
                    salesgroup_id=:sg, sales_name=:sn,
                    responsible_name=:pam, pillar=:p, solution=:s, service=:svc,
                    brand=:b, company_name=:cn, vertical_industry=:vi, distributor_name=:dn,
                    updated_at=NOW()
                WHERE uid=:ouid
            """)
            
            conn.execute(upd_q, {
                "nuid": new_uid, "noid": new_opp_id, "npid": new_product_id_code,
                "sg": payload['salesgroup_id'], "sn": payload['sales_name'], 
                "pam": payload['responsible_name'], "p": payload['pillar'], 
                "s": payload['solution'], "svc": payload['service'],
                "b": payload['brand'], "cn": payload['company_name'],
                "vi": payload['vertical_industry'], "dn": payload['distributor_name'],
                "ouid": payload['uid']
            })
            
            # 6. LOGGING PERUBAHAN FIELD
            fields_to_track = {
                'salesgroup_id': 'Sales Group',
                'sales_name': 'Sales Name',
                'responsible_name': 'PAM',
                'pillar': 'Pillar',
                'solution': 'Solution',
                'service': 'Service',
                'brand': 'Brand',
                'company_name': 'Company',
                'distributor_name': 'Distributor'
            }
            
            for db_field, label in fields_to_track.items():
                old_val = str(old_data[db_field]) if old_data[db_field] else ""
                new_val = str(payload[db_field]) if payload[db_field] else ""
                
                if old_val != new_val:
                    current_ts = get_now_jakarta()
                    log_q = text("""
                        INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value)
                        VALUES (:ts, :oname, :u, 'EDIT', :fld, :ov, :nv)
                    """)
                    conn.execute(log_q, {
                        "ts": current_ts,
                        "oname": old_data['opportunity_name'],
                        "u": payload['user'],
                        "fld": label,
                        "ov": old_val,
                        "nv": new_val
                    })

            # Log jika UID berubah
            if old_data['uid'] != new_uid:
                conn.execute(text("""
                    INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value)
                    VALUES (NOW(), :oname, :u, 'EDIT', 'UID Regeneration', :ov, :nv)
                """), {"oname": old_data['opportunity_name'], "u": payload['user'], "ov": old_data['uid'], "nv": new_uid})
            
            return {"status": 200, "message": "Full Data Updated!", "data": {"uid": new_uid}}
            
    except Exception as e:
        return {"status": 500, "message": str(e)}

# def update_opportunity_stage_bulk_enhanced(opp_id, new_stage, notes, manual_date, user, closing_reason=None):
#     try:
#         with engine.begin() as conn:
#             # 1. Update Tabel Opportunities (Detail)
#             params = {"stg": new_stage, "note": notes, "date": manual_date, "oid": opp_id}
            
#             if closing_reason:
#                 query_upd = text("""
#                     UPDATE opportunities 
#                     SET stage = :stg, stage_notes = :note, closing_reason = :reason, closing_notes = :note, updated_at = :date
#                     WHERE opportunity_id = :oid
#                 """)
#                 params["reason"] = closing_reason
#             else:
#                 query_upd = text("""
#                     UPDATE opportunities 
#                     SET stage = :stg, stage_notes = :note, updated_at = :date
#                     WHERE opportunity_id = :oid
#                 """)
            
#             conn.execute(query_upd, params)

#             # --- [SYNC] SYNC UPDATE KE TABEL SALES_OPPORTUNITIES (HEADER) ---
#             if closing_reason:
#                 query_sales = text("""
#                     UPDATE sales_opportunities
#                     SET stage = :stg, closing_reason = :reason, sales_notes = :note, updated_at = :date
#                     WHERE opportunity_id = :oid
#                 """)
#             else:
#                 query_sales = text("""
#                     UPDATE sales_opportunities
#                     SET stage = :stg, sales_notes = :note, updated_at = :date
#                     WHERE opportunity_id = :oid
#                 """)
            
#             conn.execute(query_sales, params)

#             # 2. Log Activity
#             log_msg = f"Stage updated to {new_stage}"
#             if closing_reason: log_msg += f" (Reason: {closing_reason})"
            
#             conn.execute(text("""
#                 INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, new_value)
#                 VALUES (NOW(), :oid, :usr, 'UPDATE', 'Stage Progression', :val)
#             """), {"oid": opp_id, "usr": user, "val": log_msg})
            
#             return {"status": 200, "message": "Stage updated successfully."}

#     except Exception as e:
#         return {"status": 500, "message": str(e)}

def add_master_company(company_name, vertical_industry):
    """Menambahkan perusahaan baru ke master data jika belum ada."""
    try:
        with engine.begin() as conn:
            check_q = text("SELECT company_name FROM companies WHERE company_name = :name LIMIT 1")
            existing = conn.execute(check_q, {"name": company_name}).first()
            
            if not existing:
                ins_q = text("INSERT INTO companies (company_name, vertical_industry) VALUES (:name, :vert)")
                conn.execute(ins_q, {"name": company_name, "vert": vertical_industry})
                return {"status": 200, "message": "New company added to master data."}
            else:
                return {"status": 200, "message": "Company already exists."}
    except Exception as e:
        return {"status": 500, "message": f"Failed to add company: {str(e)}"}

# ==============================================================================
# SECTION 4: CPS OPPORTUNITY LOGIC (NEW TAB 7)
# ==============================================================================

# def generate_cps_id(sales_group_id):
#     try:
#         with engine.connect() as conn:
#             query = text("SELECT cps_id FROM cps_opportunities ORDER BY created_at DESC LIMIT 1")
#             result = conn.execute(query).fetchone()
            
#             new_sequence = 1
#             if result and result[0]:
#                 last_id = result[0]
#                 try: new_sequence = int(last_id[-4:]) + 1
#                 except: pass
            
#             return f"CPS-{sales_group_id}{str(new_sequence).zfill(4)}"
#     except Exception as e:
#         return f"CPS-{sales_group_id}{int(time.time())}"

# def add_cps_opportunity(parent_data, cps_lines):
#     try:
#         cps_id = generate_cps_id(parent_data['salesgroup_id'])
        
#         ms_map = {"Easy Access": "MS1", "Easy Guard": "MS2", "Easy Connect": "MS3"}
#         so_map = {"No Service Offering": "S1", "Full Stack": "S2", "WiFi Only": "S3"}
#         p_map = {"Launch": "P1", "Growth": "P2", "Accelerate": "P3"}
#         sla_map = {"Core": "SLA1", "Pro": "SLA2", "Elite": "SLA3"}
#         se_map = {"Internal": "SE1", "Subcont": "SE2"}
        
#         timestamp_now = int(time.time())
#         created_at = get_now_jakarta()
        
#         with engine.begin() as conn:
#             for i, line in enumerate(cps_lines):
#                 uid = f"{cps_id}-{timestamp_now}-{i}"
                
#                 ms_code = ms_map.get(line['managed_service'], "MS0")
#                 so_code = so_map.get(line['service_offering'], "S1") 
#                 p_code = p_map.get(line['package'], "P0")
#                 sla_code = sla_map.get(line['sla_level'], "SLA0")
#                 se_code = se_map.get(line['service_execution'], "SE0")
                
#                 cps_product_id = f"{ms_code}-{so_code}-{p_code}-{sla_code}-{se_code}"
                
#                 query = text("""
#                     INSERT INTO cps_opportunities (
#                         uid, cps_id, cps_product_id,
#                         managed_service, service_offering, package, sla_level, service_execution,
#                         presales_name, salesgroup_id, sales_name, responsible_name,
#                         company_name, vertical_industry, stage,
#                         opportunity_name, start_date,
#                         cost, notes, created_at, updated_at
#                     ) VALUES (
#                         :uid, :cps_id, :prod_id,
#                         :ms, :so, :pkg, :sla, :se,
#                         :pname, :sgid, :sname, :pam,
#                         :comp, :vert, :stg,
#                         :oname, :sdate,
#                         :cost, :note, :now, :now
#                     )
#                 """)
                
#                 conn.execute(query, {
#                     "uid": uid, "cps_id": cps_id, "prod_id": cps_product_id,
#                     "ms": line['managed_service'], "so": line['service_offering'],
#                     "pkg": line['package'], "sla": line['sla_level'], "se": line['service_execution'],
#                     "cost": line['cost'], "note": line['notes'],
#                     "pname": parent_data['presales_name'], "sgid": parent_data['salesgroup_id'],
#                     "sname": parent_data['sales_name'], "pam": parent_data['responsible_name'],
#                     "comp": parent_data['company_name'], "vert": parent_data['vertical_industry'],
#                     "stg": parent_data['stage'], "oname": parent_data['opportunity_name'],
#                     "sdate": parent_data['start_date'], "now": created_at
#                 })
            
#             log_msg = f"Created CPS Opp: {cps_id} ({len(cps_lines)} configs)"
#             conn.execute(text("""
#                 INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, new_value) 
#                 VALUES (:now, :oid, :usr, 'CREATE', 'CPS Opportunity', :val)
#             """), {"now": created_at, "oid": cps_id, "usr": parent_data['presales_name'], "val": log_msg})
            
#         return {"status": 200, "message": f"Success! Generated ID: {cps_id} with {len(cps_lines)} configurations."}

#     except Exception as e:
#         return {"status": 500, "message": str(e)}