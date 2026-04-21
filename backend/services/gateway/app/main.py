"""
gateway/app/main.py — DeepTrust API Gateway
=============================================
Single entry point for the React frontend.
Routes requests to the correct backend service.

Routes:
    GET  /health              → aggregates all service health
    POST /api/analyze         → routes to V1 (classic) or V2 (trained ensemble)
    POST /api/upload          → Analysis Service file upload
    GET  /api/status/{id}     → Analysis Service job status
    ANY  /auth/*              → Auth Service
"""

import os
import logging
import httpx
from fastapi import FastAPI, File, UploadFile, Query, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from pathlib import Path

# Configure structured logging for the gateway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Gateway] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs configuration. 
# In production, these are injected via environment variables (Docker/K8s).
# Defaults point to localhost for development/standalone execution.
AUTH_SERVICE_URL     = os.getenv("AUTH_SERVICE_URL",     "http://localhost:8001")
ANALYSIS_SERVICE_URL = os.getenv("ANALYSIS_SERVICE_URL", "http://localhost:8002")
MODELS_SERVICE_URL   = os.getenv("MODELS_SERVICE_URL",   "http://localhost:8003")
DEEPTRUST_V2_URL     = os.getenv("DEEPTRUST_V2_URL",     "http://localhost:8090")

# Unified timeout configuration for all downstream service calls.
# ML inference tasks are computationally expensive and may require significant processing time.
TIMEOUT = httpx.Timeout(120.0)

app = FastAPI(
    title="DeepTrust API Gateway",
    description="Orchestration layer for deepfake detection services.",
    version="1.0.0",
    docs_url="/docs"
)

# Standard CORS configuration to support cross-origin requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins     = os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """
    Consolidated health check.
    
    Probes all downstream microservices and returns an aggregated health status.
    This endpoint is critical for infrastructure monitoring and high availability.
    
    Returns:
        dict: Status of the gateway and all connected services.
    """
    services = {
        "auth":         AUTH_SERVICE_URL,
        "analysis":     ANALYSIS_SERVICE_URL,
        "models_v1":    MODELS_SERVICE_URL,
        "models_v2":    DEEPTRUST_V2_URL,
    }
    
    statuses = {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        for name, url in services.items():
            try:
                # Attempt to ping the health endpoint of each service
                r = await client.get(f"{url}/health")
                statuses[name] = r.json().get("status", "unknown")
            except Exception as e:
                logger.warning(f"Service '{name}' at {url} is unreachable: {e}")
                statuses[name] = "unreachable"

    # The gateway is considered healthy only if all downstream dependencies are also healthy
    overall = "healthy" if all(s == "healthy" for s in statuses.values()) else "degraded"
    
    return {
        "status":   overall,
        "service":  "gateway",
        "version":  "1.0.0",
        "services": statuses
    }


@app.get("/")
async def root():
    """ Discovery endpoint describing available detection pipelines. """
    return {
        "message": "DeepTrust API Gateway",
        "docs":    "/docs",
        "models":  {
            "v1": "Classic lightweight models based on heuristics and traditional ML.",
            "v2": "State-of-the-art ensemble (MesoNet V2 + XceptionNet V2) with 95.52% DFDC accuracy."
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Analysis Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(
    file:          UploadFile = File(...),
    model_version: str        = Query("v2", description="'v1' = classic models, 'v2' = production-grade ensemble"),
    gradcam:       bool       = Query(True,  description="Whether to generate Grad-CAM visual explanations (V2 only)"),
    authorization: Optional[str] = Header(None)
):
    """
    Main entry point for deepfake analysis requests.
    
    Intelligently routes the uploaded file to the appropriate inference service 
    based on the requested model version.
    
    Args:
        file (UploadFile): Image or video file to be analyzed.
        model_version (str): The detection pipeline to use ('v1' or 'v2').
        gradcam (bool): Flag to enable/disable visual explanation generation.
        authorization (str): Optional bearer token for tracking/authorization.
        
    Returns:
        dict: Prediction results proxied from the target inference service.
    """
    file_bytes = await file.read()

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:

        if model_version == "v2":
            # ── Production Route: DeepTrust V2 ───────────────────────────────
            logger.info(f"Routing to V2 pipeline: {file.filename}")
            try:
                # Determine pipeline (image vs video) based on file extension
                suffix = Path(file.filename).suffix.lower()
                is_video = suffix in {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

                if is_video:
                    # Video analysis uses a sampled frame approach
                    endpoint = f"{DEEPTRUST_V2_URL}/predict/video?n_frames=16&gradcam=false"
                else:
                    # Image analysis supports full XAI visualization via Grad-CAM
                    endpoint = f"{DEEPTRUST_V2_URL}/predict/image?gradcam={str(gradcam).lower()}"

                r = await client.post(
                    endpoint,
                    files={"file": (file.filename, file_bytes, file.content_type)}
                )
                
                if r.status_code != 200:
                    raise HTTPException(status_code=r.status_code, detail=f"V2 Service Error: {r.text}")
                
                # Transform response for consumption by the frontend
                data = r.json()
                data["routed_to"] = "deeptrust-v2"
                data["model_version"] = "v2"
                return data

            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail="DeepTrust V2 service unreachable. Is it running on port 8080?"
                )

        else:
            # ── Route to classic Models Service (V1 baseline) ─────────────────
            logger.info(f"[Gateway] → V1 classic: {file.filename}")
            try:
                r = await client.post(
                    f"{MODELS_SERVICE_URL}/predict",
                    files={"file": (file.filename, file_bytes, file.content_type)}
                )
                
                if r.status_code != 200:
                    raise HTTPException(status_code=r.status_code, detail=f"V1 Service Error: {r.text}")
                
                data = r.json()
                data["routed_to"]     = "models-v1"
                data["model_version"] = "v1"
                data["ensemble_version"] = "v1"
                data["ensemble_info"] = {
                    "note": (
                        "Baseline models for academic comparison. "
                        "Provides high-speed heuristic analysis."
                    )
                }
                return data

            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail="Models V1 service unreachable. Is it running on port 8003?"
                )


# ─────────────────────────────────────────────────────────────────────────────
# Upload (passes through to Analysis Service with auth)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload(
    file:          UploadFile          = File(...),
    authorization: Optional[str]       = Header(None)
):
    """
    Proxies file upload requests to the Analysis Service.
    
    This endpoint handles the initial persistence of media into the object 
    storage (MinIO) and creates a corresponding database tracking record.
    """
    file_bytes = await file.read()
    headers    = {}
    if authorization:
        headers["Authorization"] = authorization

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.post(
                f"{ANALYSIS_SERVICE_URL}/upload/",
                files={"file": (file.filename, file_bytes, file.content_type)},
                headers=headers
            )
            return JSONResponse(status_code=r.status_code, content=r.json())
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Analysis Service unreachable")


@app.get("/api/status/{analysis_id}")
async def get_status(
    analysis_id:   str,
    authorization: Optional[str] = Header(None)
):
    """
    Queries the status of a specific analysis job.
    
    Args:
        analysis_id (str): The unique UUID assigned during the upload phase.
        authorization (str): Authentication header from the frontend client.
    """
    headers = {}
    if authorization:
        headers["Authorization"] = authorization

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.get(
                f"{ANALYSIS_SERVICE_URL}/upload/status/{analysis_id}",
                headers=headers
            )
            return JSONResponse(status_code=r.status_code, content=r.json())
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Analysis Service unreachable")


# ─────────────────────────────────────────────────────────────────────────────
# Auth passthrough
# ─────────────────────────────────────────────────────────────────────────────

@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(path: str, request: Request):
    """
    Transparent reverse-proxy for all authentication and user management traffic.
    
    Routes traffic to the identity provider service (Auth Service) without 
    modifying its contents.
    
    Args:
        path (str): The specific auth endpoint being hit (e.g., 'token', 'register', 'me').
        request (Request): The incoming request object containing headers and body.
    """
    body    = await request.body()
    headers = dict(request.headers)
    
    # Remove the 'host' header to prevent infinite loops and ensure correct proxying
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            r = await client.request(
                method  = request.method,
                url     = f"{AUTH_SERVICE_URL}/{path}",
                content = body,
                headers = headers,
                params  = dict(request.query_params)
            )
            return JSONResponse(status_code=r.status_code, content=r.json())
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Auth service unreachable")