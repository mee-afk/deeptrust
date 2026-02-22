"""
DeepTrust Analysis Service
Handles file uploads and orchestrates deepfake detection.
"""
from fastapi import FastAPI, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

from shared.database.base import get_db, check_db_connection
from shared.schemas import HealthResponse
from app.routes import upload

# Initialize app
app = FastAPI(
    title="DeepTrust Analysis Service",
    description="File upload and deepfake detection orchestration",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)


@app.on_event("startup")
async def startup():
    print("🚀 Starting Analysis Service...")
    if check_db_connection():
        print("✅ Database connected")
    else:
        print("⚠️  Database connection check failed")


@app.get("/", response_model=dict)
async def root():
    return {
        "message": "DeepTrust Analysis Service",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "degraded",
        "service": "analysis",
        "version": "1.0.0",
        "database": "connected" if db_status else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)