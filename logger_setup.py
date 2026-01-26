import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    """
    Mengkonfigurasi sistem logging agar menulis ke file 'presales_app.log'.
    Fitur:
    - Rotating: File tidak akan membesar tanpa batas (Max 5MB per file).
    - Format: Waktu - Level - Pesan.
    - Singleton: Mencegah duplikasi log saat Streamlit re-run.
    """
    
    # Nama logger
    logger = logging.getLogger("PresalesApp")
    
    # Set level log (INFO artinya catat Info, Warning, dan Error)
    logger.setLevel(logging.INFO)
    
    # Cek apakah handler sudah ada (agar tidak double saat re-run)
    if not logger.handlers:
        # 1. Buat Handler untuk menulis ke File
        # maxBytes=5*1024*1024 artinya 5MB. backupCount=3 artinya simpan 3 file terakhir.
        file_handler = RotatingFileHandler("presales_app.log", maxBytes=5*1024*1024, backupCount=3)
        
        # 2. Atur Format Tulisan
        # Contoh: 2026-01-19 10:00:00 - ERROR - Database connection failed
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 3. Pasang Handler ke Logger
        logger.addHandler(file_handler)
        
        # (Opsional) Tambahkan juga logging ke Terminal VS Code
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

# Inisialisasi logger agar bisa langsung diimport
logger = setup_logger()