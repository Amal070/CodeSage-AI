# ============================================================
# CodeSage AI - FastAPI Main Application
# ============================================================

# -------------------- FastAPI Imports -----------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# -------------------- Python Standard Library ---------------

import logging
import platform
import time

logger = logging.getLogger("codesage.main")


# Import the SQLAlchemy engine.
# The engine is configured in app/database.py and connects
# FastAPI to the PostgreSQL database.
from app.database import engine

# Import the API routers
from app.api.auth import router as auth_router
from app.api.project import router as project_router
from app.api.ai import router as ai_router
from app.api.docs import router as docs_router



# ============================================================
# CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="CodeSage AI",
    description="AI-Powered Code Understanding Platform",
    version="1.0.0"
)


# ============================================================
# CORS CONFIGURATION
# ============================================================

# These are the frontend URLs allowed to communicate
# with the FastAPI backend during local development.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


app.add_middleware(
    CORSMiddleware,

    # Allow requests from the React/Vite frontend.
    allow_origins=origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",

    # Allow cookies and authentication credentials.
    allow_credentials=True,

    # Allow GET, POST, PUT, DELETE, etc.
    allow_methods=["*"],

    # Allow all request headers.
    allow_headers=["*"],
)


# ============================================================
# INCLUDE ROUTERS
# ============================================================

app.include_router(auth_router, prefix="/api")
app.include_router(project_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(docs_router, prefix="/api")



# ============================================================
# APPLICATION START TIME
# ============================================================

# Used by the system-info endpoint to calculate
# how long the backend has been running.
START_TIME = time.time()


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "Welcome to CodeSage AI Backend 🚀",
        "status": "online"
    }


# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "OK",
        "timestamp": time.time()
    }


# ============================================================
# SYSTEM INFORMATION ENDPOINT
# ============================================================

@app.get("/api/system-info")
def system_info():

    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": int(time.time() - START_TIME),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "framework": "FastAPI"
    }


# ============================================================
# DATABASE CONNECTION TEST
# ============================================================

@app.get("/db-test")
def database_test():

    try:

        # Try opening a connection to PostgreSQL.
        # If this succeeds, FastAPI can communicate
        # with the codesage_db PostgreSQL database.
        with engine.connect():

            return {
                "status": "success",
                "message": "PostgreSQL connected successfully"
            }

    except Exception as e:
        logger.error("Database connection check failed: %s", e)
        return {
            "status": "error",
            "message": "Database connection failed"
        }