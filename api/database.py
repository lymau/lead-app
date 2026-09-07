import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

logger = logging.getLogger(__name__)

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
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
