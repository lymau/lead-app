import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
import pandas as pd

logger = logging.getLogger(__name__)

MASTER_QUERIES = {
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

def get_master_data(db: Session, action: str) -> List[Dict[str, Any]]:
    if action in MASTER_QUERIES:
        try:
            df = pd.read_sql(text(MASTER_QUERIES[action]), db.bind)
            # Replace NaN with None for clean JSON serialization
            df = df.where(pd.notnull(df), None)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"DB Error ({action}): {e}")
            return []
    return []

def add_master_company(db: Session, company_name: str, vertical_industry: str) -> Dict[str, Any]:
    try:
        check_q = text("SELECT company_name FROM companies WHERE company_name = :name LIMIT 1")
        existing = db.execute(check_q, {"name": company_name}).first()
        
        if not existing:
            ins_q = text("INSERT INTO companies (company_name, vertical_industry) VALUES (:name, :vert)")
            db.execute(ins_q, {"name": company_name, "vert": vertical_industry})
            db.commit()
            return {"status": 200, "message": "New company added to master data."}
        else:
            return {"status": 200, "message": "Company already exists."}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add company: {e}")
        return {"status": 500, "message": f"Failed to add company: {str(e)}"}

def add_master_distributor(db: Session, distributor_name: str) -> Dict[str, Any]:
    if not distributor_name or not distributor_name.strip():
        return {"status": 400, "message": "Distributor name cannot be empty."}
    try:
        query = text("INSERT INTO distributors (distributor_name) VALUES (:name)")
        db.execute(query, {"name": distributor_name.strip()})
        db.commit()
        return {"status": 200, "message": "Success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add distributor: {e}")
        return {"status": 500, "message": str(e)}
