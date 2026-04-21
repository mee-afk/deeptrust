"""
DeepTrust Analysis Service
==========================
This service is responsible for managing the media analysis lifecycle. 
It handles authenticated file uploads, persistence to object storage (MinIO), 
and orchestrates the deepfake detection jobs by maintaining a state in 
the central PostgreSQL database.

Key Responsibilities:
- Managing media upload sessions and object storage integration.
- Tracking analysis progress and surfacing results via a unified status API.
- Validating file integrity and security before processing.
"""

from fastapi import FastAPI, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os

# Import shared components for database consistency
from shared.database.base import get_db, check_db_connection
from shared.schemas import HealthResponse
from app.routes import upload

# Service instance initialization
app = FastAPI(
    title="DeepTrust Analysis Service",
    description="Orchestration engine for media persistence and detection lifecycle.",
    version="1.0.0"
)

# Standard CORS configuration for frontend and gateway cross-origin communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach specialized routers for different logical domains
app.include_router(upload.router)


@app.on_event("startup")
async def startup():
    """ Sequence of operations to execute when the service starts. """
    print("Initiating Analysis Service sequence...")
    # Verify that the persistent data store is reachable
    if check_db_connection():
        print("Database connectivity verified.")
    else:
        print("Critical Error: Database unreachable during service startup.")


@app.get("/", response_model=dict)
async def root():
    """ Information endpoint providing a map of available analysis resources. """
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
    """ Aggregate health status endpoint for infrastructure monitoring. """
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "degraded",
        "service": "analysis",
        "version": "1.0.0",
        "database": "connected" if db_status else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    # Local executable entry point on port 8002
    uvicorn.run(app, host="0.0.0.0", port=8002)