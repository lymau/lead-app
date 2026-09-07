from datetime import datetime, timedelta

def get_now_jakarta() -> datetime:
    """Mengembalikan waktu saat ini dalam zona waktu WIB (UTC+7)."""
    return datetime.utcnow() + timedelta(hours=7)
