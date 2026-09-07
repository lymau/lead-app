# 🚀 ISSUE: Buat FastAPI Service dari `backend.py`

**Tipe:** Feature / Refactoring  
**Prioritas:** High  
**Assigned to:** Junior Developer / AI Agent  
**Estimasi:** 2–3 hari kerja  

---

## 📋 Latar Belakang & Tujuan

Aplikasi ini saat ini menggunakan **Streamlit** sebagai frontend sekaligus backend. Semua logika database berada di file `backend.py`. Masalahnya, logika bisnis tersebut sangat terikat dengan Streamlit (`st.secrets`, `st.error`, `st.stop()`, dsb.) sehingga **tidak bisa digunakan oleh aplikasi lain** (mobile app, React, dsb.).

**Tujuan issue ini** adalah memisahkan logika bisnis menjadi sebuah **API Service mandiri** menggunakan **FastAPI**, sehingga:

1. Frontend Streamlit bisa memanggil API ini melalui HTTP.
2. Aplikasi klien lain (mobile, web) bisa mengonsumsi API yang sama.
3. Kode lebih mudah di-test dan di-maintain.

---

## 📁 Struktur Proyek yang Harus Dibuat

Buat folder baru `api/` di root proyek dengan struktur berikut:

```
lead-app/
├── api/
│   ├── main.py              # Entry point FastAPI app
│   ├── config.py            # Konfigurasi dari environment variables (.env)
│   ├── database.py          # Setup SQLAlchemy engine & session
│   ├── dependencies.py      # Dependency Injection (get_db)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoint autentikasi & manajemen user
│   │   ├── leads.py         # Endpoint CRUD opportunities/leads
│   │   ├── master.py        # Endpoint master data (presales, brand, dll.)
│   │   └── notifications.py # Endpoint email & reminder
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py          # Pydantic models untuk request/response auth
│   │   ├── lead.py          # Pydantic models untuk opportunities
│   │   └── master.py        # Pydantic models untuk master data
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py          # Logika autentikasi
│   │   ├── lead_service.py          # Logika CRUD leads/opportunities
│   │   ├── master_service.py        # Logika master data
│   │   └── notification_service.py  # Logika kirim email
│   ├── .env.example         # Template environment variables
│   └── requirements-api.txt # Dependencies khusus API
```

---

## ⚙️ Setup & Konfigurasi

### 1. File `api/requirements-api.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.44
psycopg2-binary==2.9.11
pandas==2.3.0
python-dotenv==1.0.0
pydantic==2.7.0
pydantic-settings==2.3.0
```

### 2. File `api/.env.example`

```env
# Database
DB_USERNAME=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name

# SMTP Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=noreply@example.com
SMTP_PASSWORD=your_email_app_password

# API Security
API_SECRET_KEY=your-very-secret-key-here
```

### 3. File `api/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_username: str
    db_password: str
    db_host: str
    db_port: int = 5432
    db_name: str

    smtp_server: str
    smtp_port: int = 587
    smtp_email: str
    smtp_password: str

    api_secret_key: str = "changeme"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 🗄️ Database Setup

### File `api/database.py`

> **PENTING:** Hapus semua referensi ke `st.secrets`, `st.error()`, dan `st.stop()`. Gunakan variabel environment melalui `config.py`.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

DATABASE_URL = (
    f"postgresql+psycopg2://{settings.db_username}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### File `api/dependencies.py`

```python
from .database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 📐 Pydantic Schemas

Buat schema untuk **validasi request dan response** di folder `api/schemas/`.

### `api/schemas/auth.py`

```python
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: int
    data: Optional[dict] = None
    message: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    username: str
    new_password: str
```

### `api/schemas/lead.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class ProductLine(BaseModel):
    pillar: str
    solution: str
    service: str
    pillar_product: Optional[str] = None
    solution_product: Optional[str] = None
    brand: Optional[str] = None
    channel: Optional[str] = None
    distributor_name: Optional[str] = None
    cost: Optional[float] = 0
    notes: Optional[str] = ""

class CreateOpportunityRequest(BaseModel):
    # Parent data
    presales_name: str
    salesgroup_id: str
    sales_name: str
    responsible_name: str
    opportunity_name: str
    start_date: date
    company_name: str
    vertical_industry: str
    stage: Optional[str] = "Open"
    route_to_market: Optional[str] = "Direct"
    # Product lines
    product_lines: List[ProductLine]

class UpdateLeadRequest(BaseModel):
    uid: str
    user: str
    cost: Optional[float] = None
    notes: Optional[str] = None

class UpdateFullOpportunityRequest(BaseModel):
    uid: str
    user: str
    salesgroup_id: str
    sales_name: str
    responsible_name: str
    pillar: str
    pillar_product: Optional[str] = None
    solution: str
    solution_product: Optional[str] = None
    service: str
    brand: Optional[str] = None
    company_name: str
    vertical_industry: str
    distributor_name: Optional[str] = None
    start_date: date
    route_to_market: str

class UpdateStageRequest(BaseModel):
    opportunity_id: str
    new_stage: str
    user_actor: str
    po_boq_link: Optional[str] = None
    project_id: Optional[str] = None
```

### `api/schemas/master.py`

```python
from pydantic import BaseModel

class AddCompanyRequest(BaseModel):
    company_name: str
    vertical_industry: str

class AddDistributorRequest(BaseModel):
    distributor_name: str
```

---

## 🔌 Endpoints yang Harus Dibuat

Berikut adalah **daftar lengkap semua endpoint** yang harus dibuat beserta referensi ke fungsi asli di `backend.py`:

---

### Router: `api/routers/auth.py`

| Method | Path | Fungsi di backend.py | Deskripsi |
|--------|------|---------------------|-----------|
| `POST` | `/auth/login` | `validate_presales_login()` | Login user presales |
| `POST` | `/auth/change-password` | `change_user_password()` | Ganti password user |
| `GET` | `/auth/users` | `get_presales_users_list()` | Ambil daftar semua username |

**Contoh implementasi:**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..dependencies import get_db
from ..schemas.auth import LoginRequest, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    query = text(
        "SELECT presales_name, email, need_password_change, access_group "
        "FROM presales WHERE presales_name = :u AND password = :p"
    )
    row = db.execute(query, {"u": request.username, "p": request.password}).mappings().fetchone()
    if row:
        return {"status": 200, "data": dict(row)}
    return {"status": 401, "message": "Nama atau Password salah."}

@router.post("/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    query = text(
        "UPDATE presales SET password = :np, need_password_change = FALSE "
        "WHERE presales_name = :u"
    )
    db.execute(query, {"np": request.new_password, "u": request.username})
    db.commit()
    return {"status": 200, "message": "Password berhasil diubah!"}

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT presales_name FROM presales ORDER BY presales_name")).fetchall()
    return [row[0] for row in result]
```

---

### Router: `api/routers/master.py`

| Method | Path | Fungsi di backend.py | Deskripsi |
|--------|------|---------------------|-----------|
| `GET` | `/master/presales` | `get_master_presales("getPresales")` | Daftar presales & email |
| `GET` | `/master/pam-mapping` | `get_master_presales("getPAMMapping")` | Mapping inputter ke PAM |
| `GET` | `/master/brands` | `get_master_presales("getBrands")` | Daftar brand & channel |
| `GET` | `/master/pillars` | `get_master_presales("getPillars")` | Daftar pillar/solution/service |
| `GET` | `/master/stages` | `get_master_presales("getPresalesStages")` | Daftar stage presales |
| `GET` | `/master/sales-groups` | `get_master_presales("getSalesGroups")` | Daftar sales group |
| `GET` | `/master/sales-names` | `get_master_presales("getSalesNames")` | Daftar nama sales |
| `GET` | `/master/responsibles` | `get_master_presales("getResponsibles")` | Daftar responsible/PAM |
| `GET` | `/master/companies` | `get_master_presales("getCompanies")` | Daftar perusahaan |
| `GET` | `/master/distributors` | `get_master_presales("getDistributors")` | Daftar distributor |
| `GET` | `/master/opportunities` | `get_master_presales("getOpportunities")` | Daftar nama opportunity |
| `GET` | `/master/activity-log` | `get_master_presales("getActivityLog")` | Activity log global (1000 baris) |
| `POST` | `/master/companies` | `add_master_company()` | Tambah perusahaan baru |
| `POST` | `/master/distributors` | `add_master_distributor()` | Tambah distributor baru |

Untuk endpoint GET master data, salin query SQL yang sudah ada di dictionary `queries` di `backend.py` (fungsi `get_master_presales()`).

---

### Router: `api/routers/leads.py`

| Method | Path | Fungsi di backend.py | Deskripsi |
|--------|------|---------------------|-----------|
| `GET` | `/leads` | `get_leads_by_group_logic(username)` | Ambil semua leads berdasarkan akses user |
| `GET` | `/leads/{uid}` | `get_lead_by_uid(uid)` | Ambil 1 lead berdasarkan UID |
| `GET` | `/leads/opportunity/{opp_id}/summary` | `get_opportunity_summary(opp_id)` | Preview ringkasan opportunity |
| `GET` | `/leads/activity-log` | `get_activity_log_by_group(username)` | Activity log berdasarkan group user |
| `POST` | `/leads` | `add_multi_line_opportunity()` | Buat opportunity baru (multi-line) |
| `PUT` | `/leads/cost-notes` | `update_lead()` | Update cost & notes saja |
| `PUT` | `/leads/full` | `update_full_opportunity()` | Update semua field opportunity |
| `PUT` | `/leads/stage` | `update_opportunity_stage()` | Update stage seluruh opportunity |
| `DELETE` | `/leads/{uid}` | `delete_opportunity_by_uid()` | Hapus 1 baris opportunity |

**Catatan penting untuk `GET /leads`:**  
Parameter `username` dikirim sebagai query parameter: `GET /leads?username=JohnDoe`

```python
@router.get("/leads")
def get_leads(username: str, db: Session = Depends(get_db)):
    # Salin logika dari get_leads_by_group_logic() di backend.py
    # Ganti semua penggunaan engine/conn dengan db
    ...
```

---

### Router: `api/routers/notifications.py`

| Method | Path | Fungsi di backend.py | Deskripsi |
|--------|------|---------------------|-----------|
| `POST` | `/notifications/send-email` | `send_email_notification()` | Kirim email HTML |
| `POST` | `/notifications/inactive-reminder` | `check_and_remind_inactive_presales()` | Cek & kirim reminder presales tidak aktif |
| `GET` | `/notifications/registered-emails` | `get_registered_emails()` | Daftar semua email terdaftar |

Untuk `send_email_notification()`, konfigurasi SMTP harus dibaca dari `settings` (bukan `st.secrets`).

---

## 🏠 Entry Point: `api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, leads, master, notifications

app = FastAPI(
    title="Lead App API",
    description="API Service untuk Presales Lead Management System - Sisindokom",
    version="1.0.0",
)

# CORS – sesuaikan origins dengan domain frontend produksi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain spesifik di production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router, prefix="/leads")
app.include_router(master.router, prefix="/master")
app.include_router(notifications.router, prefix="/notifications")

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Lead App API"}
```

---

## ✅ Best Practices yang Wajib Diikuti

### 1. Dependency Injection untuk Database

**JANGAN** membuat `engine` global yang dipakai langsung. Selalu gunakan `Depends(get_db)` agar setiap request mendapat sesi database yang terisolasi dan di-close dengan benar setelah selesai.

```python
# SALAH - Jangan lakukan ini
engine = create_engine(...)
with engine.connect() as conn:
    ...

# BENAR - Gunakan Depends
@router.get("/endpoint")
def my_endpoint(db: Session = Depends(get_db)):
    db.execute(...)
```

### 2. Konsistensi Error Handling

Gunakan `HTTPException` dari FastAPI untuk error yang berkaitan dengan HTTP status code.

```python
from fastapi import HTTPException

@router.get("/leads/{uid}")
def get_lead(uid: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("SELECT * FROM opportunities WHERE uid = :uid"),
        {"uid": uid}
    ).mappings().fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="UID tidak ditemukan")
    return {"status": 200, "data": dict(result)}
```

### 3. Validasi Input dengan Pydantic

Semua data yang masuk ke endpoint `POST` dan `PUT` **harus** menggunakan Pydantic model (schema). Jangan terima `dict` atau `Any` mentah.

### 4. Hapus Semua Referensi `st.*`

Di `backend.py`, banyak error handling yang memanggil `st.error()` dan `st.stop()`. Ganti semua itu:

```python
# HAPUS INI (Streamlit)
st.error("Config tidak ditemukan")
st.stop()

# GANTI DENGAN INI (FastAPI)
raise HTTPException(status_code=500, detail="Konfigurasi database tidak ditemukan")
```

### 5. Logging Standar Python

Gunakan `logging` standar, bukan `print()`:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Opportunity created: %s", opportunity_name)
logger.error("Database error: %s", str(e))
```

### 6. Timestamp Jakarta (WIB)

Pindahkan helper function ini ke `api/utils.py`:

```python
from datetime import datetime, timedelta

def get_now_jakarta() -> datetime:
    """Mengembalikan waktu saat ini dalam zona waktu WIB (UTC+7)."""
    return datetime.utcnow() + timedelta(hours=7)
```

### 7. Jangan Hardcode Credential

Semua konfigurasi sensitif harus dibaca dari `.env` melalui `config.py`. Tidak boleh ada string password atau URL koneksi yang ditulis langsung di dalam kode.

### 8. Commit Database Secara Eksplisit

Untuk operasi tulis (INSERT, UPDATE, DELETE), selalu panggil `db.commit()` setelah eksekusi. Gunakan `try/except` dengan `db.rollback()` jika terjadi error:

```python
try:
    db.execute(query, params)
    db.commit()
    return {"status": 200, "message": "Success"}
except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=str(e))
```

---

## 🧪 Cara Menjalankan & Testing

### Menjalankan Server

```bash
# Install dependencies
pip install -r api/requirements-api.txt

# Salin dan isi konfigurasi
cp api/.env.example api/.env
# Edit api/.env dengan kredensial yang benar

# Jalankan server development (dari root folder lead-app/)
uvicorn api.main:app --reload --port 8000
```

### Testing via Swagger UI

Buka browser dan akses: `http://localhost:8000/docs`

FastAPI secara otomatis menghasilkan dokumentasi interaktif (Swagger UI). Gunakan ini untuk test setiap endpoint tanpa perlu tools tambahan.

### Contoh Test Manual dengan `curl`

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "JohnDoe", "password": "secret"}'

# Get leads by user
curl "http://localhost:8000/leads?username=JohnDoe"

# Get single lead by UID
curl http://localhost:8000/leads/ENT1Q20001-GEN-1234567890

# Delete lead (hanya jika benar-benar perlu ditest)
curl -X DELETE "http://localhost:8000/leads/ENT1Q20001-GEN-1234567890?user_actor=JohnDoe"
```

---

## ⚠️ Gotchas — Hal-hal yang Perlu Diperhatikan

1. **Dua cara akses DB di `backend.py`**: Ada yang pakai `engine.connect()` dan ada yang pakai `conn.session` (Streamlit connection). Di FastAPI, **standarkan semuanya** menggunakan `Session` dari `Depends(get_db)`.

2. **`update_opportunity_stage()`** (line 623): Fungsi ini menggunakan `conn.session` (Streamlit). Ganti signature-nya menjadi menerima parameter `db: Session`.

3. **`delete_opportunity_by_uid()` dan `get_opportunity_by_uid()`** (line 800 & 818): Sama seperti poin 2, ganti `conn.session` dengan `db`.

4. **Tipe data tanggal**: FastAPI + Pydantic otomatis mengkonversi string ISO (`"2026-01-15"`) ke `datetime.date`. Pastikan schema menggunakan `date` dari modul `datetime`.

5. **Generate UID unik** menggunakan `time.time_ns()` sudah baik. Pertahankan logika ini di `lead_service.py`.

6. **`add_multi_line_opportunity()`** adalah fungsi paling kompleks (generate rows_id `Q2xxxx`, sync ke tabel `sales_opportunities`, insert ke `opportunities`, log activity). Salin logikanya **dengan sangat hati-hati** dan pastikan tidak ada yang terlewat.

7. **Logic akses berbeda per `access_group`** di `get_leads_by_group_logic()` harus disalin persis. Ada khusus untuk `Ade Frianche`, `TOP_MGMT`, dan berbagai group lain. Jangan disederhanakan.

---

## 📌 Definition of Done (DoD)

Issue ini dianggap **selesai** jika semua checklist berikut terpenuhi:

- [ ] Semua file dalam struktur folder `api/` telah dibuat
- [ ] Semua endpoint di tabel di atas sudah terimplementasi
- [ ] Server dapat berjalan dengan `uvicorn api.main:app --reload`
- [ ] Endpoint `/health` mengembalikan `{"status": "ok"}`
- [ ] **Tidak ada satu pun** `import streamlit` di seluruh folder `api/`
- [ ] Swagger UI dapat diakses di `http://localhost:8000/docs`
- [ ] Semua endpoint `POST` dan `PUT` menggunakan Pydantic schema
- [ ] Konfigurasi DB dan SMTP dibaca dari `.env`, bukan hardcoded
- [ ] Setiap operasi tulis (INSERT/UPDATE/DELETE) menggunakan `try/except` dengan `db.rollback()` jika error
- [ ] File `api/.env.example` tersedia sebagai template
- [ ] Tidak ada `print()` debug yang tertinggal — gunakan `logging`

---

## 📎 Referensi

- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 — Session Usage](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Pydantic v2 Docs](https://docs.pydantic.dev/latest/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- Source code asli: `backend.py` (di root project)
