import logging
import time
import re
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import pandas as pd
from ..utils import get_now_jakarta

logger = logging.getLogger(__name__)

def get_leads_by_group_logic(db: Session, username: str) -> Dict[str, Any]:
    """
    Mengambil data berdasarkan Hak Akses (Territory-based Visibility).
    """
    try:
        user_query = text("SELECT access_group FROM presales WHERE presales_name = :u")
        user_data = db.execute(user_query, {"u": username}).mappings().first()
        
        if not user_data:
            return {"status": 403, "message": "User tidak memiliki access group."}
            
        access_group = user_data['access_group']
        base_query = "SELECT * FROM opportunities WHERE start_date >= '2026-01-01'"
        
        if username == 'Ade Frianche':
            final_query = text(f"{base_query} AND (salesgroup_id IN ('NET_SPEC', 'IOH_XL', '2ND_TIER') OR presales_name IN (SELECT presales_name FROM presales WHERE access_group IN ('NET_SPEC', 'IOH_XL', '2ND_TIER')))")
        elif access_group == 'ENT_1':
            final_query = text(f"{base_query} AND salesgroup_id IN ('ENT1', 'SP1B')")
        elif access_group == 'ENT_2':
            final_query = text(f"{base_query} AND salesgroup_id = 'ENT2'")
        elif access_group == 'IOH_XL':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = 'IOH_XL')")
        elif access_group == 'SEC_TEAM':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = 'SEC_TEAM')")
        elif access_group == 'DC_TEAM':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = 'DC_TEAM')")
        elif access_group == 'NET_SPEC':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = 'NET_SPEC')")
        elif access_group == 'MS_TEAM':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = 'MS_TEAM')")
        elif access_group == '2ND_TIER':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = '2ND_TIER')")
        elif access_group == 'Herman_Group':
            final_query = text(f"{base_query} AND presales_name IN (SELECT presales_name FROM presales WHERE access_group = 'Herman_Group')")
        elif access_group in ['TOP_MGMT']:
            final_query = text(base_query)
        else:
            final_query = text(f"{base_query} AND presales_name = :u")
        
        result = db.execute(final_query, {"u": username}).mappings().fetchall()
        data_list = [dict(row) for row in result]
        
        return {"status": 200, "data": data_list}
    except Exception as e:
        logger.error(f"Error fetching leads by group for {username}: {e}")
        return {"status": 500, "message": f"Error fetching data: {str(e)}"}

def get_lead_by_uid(db: Session, uid: str) -> Dict[str, Any]:
    """Mengambil 1 lead spesifik berdasarkan UID."""
    try:
        query = text("SELECT * FROM opportunities WHERE uid = :uid LIMIT 1")
        result = db.execute(query, {"uid": uid}).mappings().first()
        if result:
            return {"status": 200, "data": dict(result)}
        return {"status": 404, "message": "UID Not Found"}
    except Exception as e:
        logger.error(f"Error getting lead by uid {uid}: {e}")
        return {"status": 500, "message": str(e)}

def get_opportunity_summary(db: Session, opp_id: str) -> Dict[str, Any]:
    """Mengambil ringkasan opportunity berdasarkan ID untuk preview."""
    try:
        query_str = text("""
            SELECT opportunity_name, company_name, stage, COUNT(uid) as total_items 
            FROM opportunities 
            WHERE opportunity_id = :oid 
            GROUP BY opportunity_name, company_name, stage
        """)
        df = pd.read_sql(query_str, db.bind, params={"oid": opp_id})
        if not df.empty:
            df = df.where(pd.notnull(df), None)
            return {"status": 200, "data": df.iloc[0].to_dict()}
        return {"status": 404, "message": "Opportunity ID not found"}
    except Exception as e:
        logger.error(f"Error getting opportunity summary for {opp_id}: {e}")
        return {"status": 500, "message": str(e)}

def get_activity_log_by_group(db: Session, username: str) -> List[Dict[str, Any]]:
    """Mengambil Log Aktivitas berdasarkan Access Group User."""
    try:
        check = db.execute(
            text("SELECT access_group FROM presales WHERE presales_name = :u"),
            {"u": username}
        ).mappings().first()
        if not check:
            return []
        user_group = check['access_group']
        
        if user_group == 'TOP_MGMT':
            query = text("""
                SELECT 
                    l.timestamp as "Timestamp", l.opportunity_name as "OpportunityName", 
                    l.user_name as "user_name", l.action as "Action", 
                    l.field as "Field", l.old_value as "OldValue", l.new_value as "NewValue" 
                FROM activity_logs l ORDER BY l.timestamp DESC LIMIT 1000
            """)
            df = pd.read_sql(query, db.bind)
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
            df = pd.read_sql(query, db.bind, params={"ug": user_group})
        
        df = df.where(pd.notnull(df), None)
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Log Error for {username}: {e}")
        return []

def add_multi_line_opportunity(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        parent_data = payload
        product_lines = payload.get('product_lines', [])

        # A. Logic Rows ID (Q2xxxx)
        chk_q = text("SELECT rows_id FROM description WHERE description = :desc LIMIT 1")
        res_desc = db.execute(chk_q, {"desc": parent_data['opportunity_name']}).mappings().first()
        
        if res_desc:
            current_rows_id = res_desc['rows_id']
        else:
            max_q = text("SELECT MAX(rows_id) FROM description WHERE rows_id LIKE 'Q2%' AND LENGTH(rows_id) = 6")
            max_val = db.execute(max_q).scalar()
            
            new_seq = 1
            if max_val:
                try:
                    new_seq = int(max_val[2:]) + 1
                except Exception:
                    pass
            
            current_rows_id = f"Q2{str(new_seq).zfill(4)}"
            db.execute(
                text("INSERT INTO description (rows_id, description) VALUES (:rid, :desc)"),
                {"rid": current_rows_id, "desc": parent_data['opportunity_name']}
            )
        
        # B. Generate Opp ID
        safe_group = parent_data.get('salesgroup_id', 'GEN')
        new_opp_id = f"{safe_group}{current_rows_id}"
        created_at = get_now_jakarta()
        created_uids = []
        
        # C. Header check in sales_opportunities
        check_header = text("SELECT opportunity_id FROM sales_opportunities WHERE opportunity_id = :oid")
        if not db.execute(check_header, {"oid": new_opp_id}).first():
            ins_header = text("""
                INSERT INTO sales_opportunities (
                    opportunity_id, opportunity_name, salesgroup_id, sales_name, 
                    stage, created_at, updated_at
                ) VALUES (
                    :oid, :oname, :sgid, :sname, 
                    :stg, :now, :now
                )
            """)
            db.execute(ins_header, {
                "oid": new_opp_id,
                "oname": parent_data['opportunity_name'],
                "sgid": parent_data['salesgroup_id'],
                "sname": parent_data['sales_name'],
                "stg": parent_data.get('stage', 'Open'),
                "now": created_at
            })
        
        # D. Loop every product line
        for line in product_lines:
            cat_q = text("SELECT pillar_id, solution_id, service_id FROM master_pillars WHERE pillar_name=:p AND solution_name=:s AND service_name=:svc LIMIT 1")
            cat = db.execute(cat_q, {"p": line['pillar'], "s": line['solution'], "svc": line['service']}).mappings().first()
            
            br_q = text("SELECT brand_id FROM brands WHERE brand_name=:b LIMIT 1")
            br = db.execute(br_q, {"b": line.get('brand')}).mappings().first()
            
            pid = cat['pillar_id'] if cat else "GEN"
            sol = str(cat['solution_id']) if cat else "0"
            svc = str(cat['service_id']) if cat else "S0"
            br_code = br['brand_id'] if br else "GEN"
            
            product_id_code = f"{pid}{sol}{svc}{br_code}".replace(" ", "").upper()
            unique_ts = time.time_ns()
            uid = f"{new_opp_id}-{product_id_code}-{unique_ts}"
            
            ins_opp = text("""
                INSERT INTO opportunities (
                    uid, opportunity_id, product_id, presales_name, salesgroup_id, 
                    sales_name, responsible_name, opportunity_name, start_date, 
                    company_name, vertical_industry, pillar, solution, service, 
                    pillar_product, solution_product, brand, channel, 
                    distributor_name, cost, notes, stage, route_to_market, 
                    created_at, updated_at
                ) VALUES (
                    :uid, :oid, :pid, :pname, :sgid, 
                    :sname, :pam, :oname, :sdate, 
                    :cname, :vi, :plr, :sol, :svc, 
                    :pp, :sp, :br, :ch, 
                    :dist, :cost, :note, :stage_val, :rtm, 
                    :now, :now
                )
            """)
            
            db.execute(ins_opp, {
                "uid": uid, "oid": new_opp_id, "pid": product_id_code,
                "pname": parent_data['presales_name'], "sgid": parent_data['salesgroup_id'], 
                "sname": parent_data['sales_name'], "pam": parent_data['responsible_name'], 
                "oname": parent_data['opportunity_name'], "sdate": str(parent_data['start_date']),
                "cname": parent_data['company_name'], "vi": parent_data['vertical_industry'],
                "plr": line['pillar'], "sol": line['solution'], "svc": line['service'],
                "pp": line.get('pillar_product', None),
                "sp": line.get('solution_product', None),
                "br": line.get('brand'), "ch": line.get('channel'), "dist": line.get('distributor_name'), 
                "cost": line.get('cost', 0), "note": line.get('notes', ''), 
                "stage_val": parent_data.get('stage', 'Open'),
                "now": created_at,
                "rtm": parent_data.get('route_to_market', 'Direct')
            })
            
            created_uids.append({"uid": uid, "opportunity_id": new_opp_id})
        
        # E. Log Activity
        log_q = text("""
            INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, new_value) 
            VALUES (:ts, :oname, :user, 'CREATE', 'New Opportunity', :val)
        """)
        db.execute(log_q, {
            "ts": created_at, "oname": parent_data['opportunity_name'], 
            "user": parent_data['presales_name'], "val": f"Created {len(product_lines)} lines. ID: {new_opp_id}"
        })
        
        db.commit()
        logger.info(f"SUCCESS: Opportunity '{parent_data['opportunity_name']}' created by {parent_data['presales_name']}")
        return {"status": 200, "message": "Opportunity successfully added!", "data": created_uids}
    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL ERROR in add_multi_line_opportunity: {str(e)}")
        return {"status": 500, "message": f"Database Error: {str(e)}"}

def update_lead(db: Session, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        current_ts = get_now_jakarta()
        uid = lead_data['uid']
        user = lead_data['user']
        new_cost = lead_data.get('cost')
        new_notes = lead_data.get('notes')

        old = db.execute(text("SELECT opportunity_name, cost, notes FROM opportunities WHERE uid=:u"), {"u": uid}).mappings().first()
        if not old:
            return {"status": 404, "message": "Data not found"}
        
        db.execute(
            text("UPDATE opportunities SET cost=:c, notes=:n, updated_at=:ts WHERE uid=:u"),
            {"c": new_cost, "n": new_notes, "u": uid, "ts": current_ts}
        )
        
        # Logging Cost Change
        old_cost_val = float(old['cost']) if old['cost'] is not None else 0.0
        new_cost_val = float(new_cost) if new_cost is not None else 0.0
        
        if abs(old_cost_val - new_cost_val) > 0.01:
            log = text("""
                INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value) 
                VALUES (:ts, :oname, :u, 'UPDATE', 'Cost', :ov, :nv)
            """)
            db.execute(log, {
                "ts": current_ts,
                "oname": old['opportunity_name'],
                "u": user, 
                "ov": f"{old_cost_val:,.0f}", 
                "nv": f"{new_cost_val:,.0f}"
            })

        # Logging Notes Change
        old_notes_val = str(old['notes']) if old['notes'] else ""
        new_notes_val = str(new_notes) if new_notes else ""
        
        if old_notes_val.strip() != new_notes_val.strip():
            log = text("""
                INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value) 
                VALUES (:ts, :oname, :u, 'UPDATE', 'Notes', :ov, :nv)
            """)
            db.execute(log, {
                "ts": current_ts,
                "oname": old['opportunity_name'],
                "u": user, 
                "ov": old_notes_val, 
                "nv": new_notes_val
            })

        db.commit()
        return {"status": 200, "message": "Updated successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating lead {lead_data.get('uid')}: {e}")
        return {"status": 500, "message": str(e)}

def update_full_opportunity(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        old_data = db.execute(text("SELECT * FROM opportunities WHERE uid=:uid"), {"uid": payload['uid']}).mappings().first()
        if not old_data:
            return {"status": 404, "message": "UID not found"}
        
        # Rows ID check
        desc_res = db.execute(text("SELECT rows_id FROM description WHERE description=:d"), {"d": old_data['opportunity_name']}).mappings().first()
        if desc_res:
            rows_id_part = desc_res['rows_id']
        else:
            match = re.search(r'(Q[1-4]\d+)', old_data['opportunity_id'])
            rows_id_part = match.group(1) if match else old_data['opportunity_id'][-6:]
        
        new_opp_id = f"{payload['salesgroup_id']}{rows_id_part}"
        
        # Category code
        cat = db.execute(
            text("SELECT pillar_id, solution_id, service_id FROM master_pillars WHERE pillar_name=:p AND solution_name=:s AND service_name=:svc LIMIT 1"),
            {"p": payload['pillar'], "s": payload['solution'], "svc": payload['service']}
        ).mappings().first()
        
        br = db.execute(text("SELECT brand_id FROM brands WHERE brand_name=:b LIMIT 1"), {"b": payload['brand']}).mappings().first()
        
        pid = cat['pillar_id'] if cat else "GEN"
        sol = str(cat['solution_id']) if cat else "0"
        svc = str(cat['service_id']) if cat else "S0"
        br_code = br['brand_id'] if br else "GEN"
        
        new_product_id_code = f"{pid}{sol}{svc}{br_code}".replace(" ", "").upper()

        parts = old_data['uid'].split('-')
        ts_part = parts[-1]
        new_uid = f"{new_opp_id}-{new_product_id_code}-{ts_part}"
        
        upd_q = text("""
            UPDATE opportunities SET
                uid=:nuid, opportunity_id=:noid, product_id=:npid,
                salesgroup_id=:sg, sales_name=:sn,
                responsible_name=:pam, pillar=:p, 
                pillar_product=:pp, solution_product=:sp,
                solution=:s, service=:svc,
                brand=:b, company_name=:cn, vertical_industry=:vi, distributor_name=:dn,
                start_date=:sd, route_to_market=:rtm,
                updated_at=NOW()
            WHERE uid=:ouid
        """)
        
        db.execute(upd_q, {
            "nuid": new_uid, "noid": new_opp_id, "npid": new_product_id_code,
            "sg": payload['salesgroup_id'], "sn": payload['sales_name'], 
            "pam": payload['responsible_name'], "p": payload['pillar'], 
            "pp": payload.get('pillar_product'),
            "sp": payload.get('solution_product'),
            "s": payload['solution'], "svc": payload['service'],
            "b": payload['brand'], "cn": payload['company_name'],
            "vi": payload['vertical_industry'], "dn": payload['distributor_name'],
            "sd": str(payload['start_date']), 
            "rtm": payload['route_to_market'],
            "ouid": payload['uid']
        })
        
        fields_to_track = {
            'salesgroup_id': 'Sales Group',
            'sales_name': 'Sales Name',
            'responsible_name': 'PAM',
            'pillar': 'Pillar',
            'solution': 'Solution',
            'service': 'Service',
            'brand': 'Brand',
            'company_name': 'Company',
            'distributor_name': 'Distributor',
            'start_date': 'Start Date',
            'route_to_market': 'Route To Market'
        }
        
        current_ts = get_now_jakarta()
        for db_field, label in fields_to_track.items():
            old_val = str(old_data[db_field]) if old_data[db_field] else ""
            new_val = str(payload.get(db_field, "")) if payload.get(db_field) else ""
            
            if old_val != new_val:
                log_q = text("""
                    INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value)
                    VALUES (:ts, :oname, :u, 'EDIT', :fld, :ov, :nv)
                """)
                db.execute(log_q, {
                    "ts": current_ts,
                    "oname": old_data['opportunity_name'],
                    "u": payload['user'],
                    "fld": label,
                    "ov": old_val,
                    "nv": new_val
                })

        if old_data['uid'] != new_uid:
            db.execute(text("""
                INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value)
                VALUES (NOW(), :oname, :u, 'EDIT', 'UID Regeneration', :ov, :nv)
            """), {"oname": old_data['opportunity_name'], "u": payload['user'], "ov": old_data['uid'], "nv": new_uid})
        
        db.commit()
        return {"status": 200, "message": "Full Data Updated!", "data": {"uid": new_uid}}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_full_opportunity: {e}")
        return {"status": 500, "message": str(e)}

def update_opportunity_stage(
    db: Session,
    opp_id: str,
    new_stage: str,
    user_actor: str,
    po_boq_link: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    try:
        q_check = text("SELECT stage, opportunity_name FROM opportunities WHERE opportunity_id = :oid LIMIT 1")
        old_data = db.execute(q_check, {"oid": opp_id}).mappings().first()
        
        if not old_data:
            return {"status": 404, "message": "Opportunity tidak ditemukan."}

        old_stage = old_data['stage']
        opp_name = old_data['opportunity_name']

        upd_q = text("""
            UPDATE opportunities 
            SET stage = :stg, 
                po_boq_link = COALESCE(:link, po_boq_link),
                project_id = COALESCE(:pid, project_id),
                updated_at = NOW() 
            WHERE opportunity_id = :oid
        """)
        
        db.execute(upd_q, {
            "stg": new_stage, 
            "oid": opp_id, 
            "link": po_boq_link, 
            "pid": project_id 
        })

        if old_stage != new_stage:
            log_q = text("""
                INSERT INTO activity_logs 
                (timestamp, opportunity_name, user_name, action, field, old_value, new_value)
                VALUES (NOW(), :oname, :usr, 'UPDATE STAGE', 'Stage', :old, :new)
            """)
            db.execute(log_q, {
                "oname": opp_name, 
                "usr": user_actor, 
                "old": str(old_stage), 
                "new": str(new_stage)
            })

        db.commit()
        return {"status": 200, "message": f"Stage seluruh baris untuk '{opp_name}' berhasil diubah menjadi {new_stage}."}
    except Exception as e:
        db.rollback()
        logger.error(f"Database error in update_opportunity_stage: {e}")
        return {"status": 500, "message": f"Database Error: {str(e)}"}

def delete_opportunity_by_uid(db: Session, uid: str, user_actor: str) -> Dict[str, Any]:
    """Menghapus 1 baris spesifik di tabel opportunities dan mencatatnya di Activity Log."""
    try:
        check_q = text("SELECT opportunity_name, solution, brand FROM opportunities WHERE uid = :uid LIMIT 1")
        row = db.execute(check_q, {"uid": uid}).mappings().first()
        
        if not row:
            return {"status": 404, "message": "Data dengan UID tersebut tidak ditemukan di database."}
        
        opp_name = row['opportunity_name']
        item_detail = f"{row['solution']} ({row['brand']})"
        
        del_q = text("DELETE FROM opportunities WHERE uid = :uid")
        db.execute(del_q, {"uid": uid})
        
        log_q = text("""
            INSERT INTO activity_logs (timestamp, opportunity_name, user_name, action, field, old_value, new_value)
            VALUES (NOW(), :opp, :usr, 'DELETE', 'Opportunity Item', :old_val, 'DELETED')
        """)
        db.execute(log_q, {
            "opp": opp_name,
            "usr": user_actor,
            "old_val": item_detail
        })
        
        db.commit()
        msg = f"Berhasil menghapus item '{item_detail}' dari proyek '{opp_name}'."
        return {"status": 200, "message": msg}
    except Exception as e:
        db.rollback()
        logger.error(f"Database error in delete_opportunity_by_uid: {e}")
        return {"status": 500, "message": f"Database Error: {e}"}
