import logging
from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def validate_presales_login(db: Session, username: str, password: str) -> Dict[str, Any]:
    query = text(
        "SELECT presales_name, email, need_password_change, access_group "
        "FROM presales WHERE presales_name = :u AND password = :p"
    )
    try:
        result = db.execute(query, {"u": username, "p": password})
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
        return {"status": 401, "message": "Nama atau Password salah."}
    except Exception as e:
        logger.error(f"Error validating login for {username}: {e}")
        return {"status": 500, "message": str(e)}

def change_user_password(db: Session, username: str, new_password: str) -> Dict[str, Any]:
    query = text("""
        UPDATE presales 
        SET password = :np, need_password_change = FALSE 
        WHERE presales_name = :u
    """)
    try:
        db.execute(query, {"np": new_password, "u": username})
        db.commit()
        return {"status": 200, "message": "Password berhasil diubah!"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password for {username}: {e}")
        return {"status": 500, "message": str(e)}

def get_presales_users_list(db: Session) -> List[str]:
    try:
        result = db.execute(text("SELECT presales_name FROM presales ORDER BY presales_name"))
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Error getting presales user list: {e}")
        return []
