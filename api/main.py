import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, leads, master, notifications

# Setup root logger for API
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lead_app_api")

app = FastAPI(
    title="Lead App API",
    description="API Service untuk Presales Lead Management System - Sisindokom",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(leads.router, prefix="/leads")
app.include_router(master.router, prefix="/master")
app.include_router(notifications.router, prefix="/notifications")

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Lead App API"}
