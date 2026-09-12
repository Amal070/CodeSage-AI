# ============================================================
# DATABASE CONNECTION
# ============================================================

import os

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

# Loads the DATABASE_URL from the .env file.
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


# ============================================================
# DATABASE URL
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not configured")


# ============================================================
# SQLALCHEMY ENGINE
# ============================================================

# Creates the connection between SQLAlchemy and PostgreSQL.
engine = create_engine(
    DATABASE_URL,
    echo=True
)


# ============================================================
# DATABASE SESSION
# ============================================================

# Creates database sessions that will later be used
# by FastAPI endpoints.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# ============================================================
# BASE CLASS
# ============================================================

# All CodeSage database models will inherit from Base.
class Base(DeclarativeBase):
    pass


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

# Provides a database session to FastAPI endpoints.
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()