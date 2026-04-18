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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Service URLs (injected by docker-compose) ─────────────────────────────────
# AUTH_SERVICE_URL     = os.getenv("AUTH_SERVICE_URL",     "http://auth:8001")
# ANALYSIS_SERVICE_URL = os.getenv("ANALYSIS_SERVICE_URL", "http://analysis:8002")
# MODELS_SERVICE_URL   = os.getenv("MODELS_SERVICE_URL",   "http://models:8003")
# DEEPTRUST_V2_URL     = os.getenv("DEEPTRUST_V2_URL",     "http://deeptrust-v2:8090")

AUTH_SERVICE_URL     = os.getenv("AUTH_SERVICE_URL",     "http://localhost:8001")
ANALYSIS_SERVICE_URL = os.getenv("ANALYSIS_SERVICE_URL", "http://localhost:8002")
MODELS_SERVICE_URL   = os.getenv("MODELS_SERVICE_URL",   "http://localhost:8003")
DEEPTRUST_V2_URL     = os.getenv("DEEPTRUST_V2_URL",     "http://localhost:8090")

TIMEOUT = httpx.Timeout(120.0)   # ML inference can take a few seconds

app = FastAPI(
    title    = "DeepTrust API Gateway",
    version  = "1.0.0",
    docs_url = "/docs"
)

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
    """Aggregate health check across all services."""
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
                r = await client.get(f"{url}/health")
                statuses[name] = r.json().get("status", "unknown")
            except Exception:
                statuses[name] = "unreachable"

    overall = "healthy" if all(s == "healthy" for s in statuses.values()) else "degraded"
    return {
        "status":   overall,
        "service":  "gateway",
        "version":  "1.0.0",
        "services": statuses
    }


@app.get("/")
async def root():
    return {
        "message": "DeepTrust API Gateway",
        "docs":    "/docs",
        "models":  {
            "v1": "Classic lightweight models (baseline)",
            "v2": "Trained ensemble — MesoNet V2 + XceptionNet V2 (95.52% DFDC accuracy)"
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Analysis Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(
    file:          UploadFile = File(...),
    model_version: str        = Query("v2", description="'v1' = classic, 'v2' = trained ensemble"),
    gradcam:       bool       = Query(True,  description="Include Grad-CAM heatmap (V2 only)"),
    authorization: Optional[str] = Header(None)
):
    """
    Main deepfake detection endpoint.

    model_version:
        v1  — Classic lightweight models (MesoNet heuristic + XceptionNet HOG +
               FrequencyAnalyzer + BiologicalAnalyzer). Kept as academic baseline.
        v2  — Trained ensemble (MesoNet trained on FF++ + XceptionNet trained on FF++,
               Platt calibrated, 95.52% DFDC accuracy). Recommended.

    The frontend model selector controls which version is called.
    """
    file_bytes = await file.read()

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:

        if model_version == "v2":
            # ── Route to DeepTrust V2 trained ensemble ────────────────────────
            logger.info(f"[Gateway] → V2 ensemble: {file.filename}")
            try:
                # r = await client.post(
                #     f"{DEEPTRUST_V2_URL}/predict/image?gradcam={str(gradcam).lower()}",
                #     files={"file": (file.filename, file_bytes, file.content_type)}
                # )
                suffix = Path(file.filename).suffix.lower()
                is_video = suffix in {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

                if is_video:
                    endpoint = f"{DEEPTRUST_V2_URL}/predict/video?n_frames=16&gradcam=false"
                else:
                    endpoint = f"{DEEPTRUST_V2_URL}/predict/image?gradcam={str(gradcam).lower()}"

                r = await client.post(
                    endpoint,
                    files={"file": (file.filename, file_bytes, file.content_type)}
                )
                if r.status_code != 200:
                    raise HTTPException(status_code=r.status_code, detail=r.text)
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
                    raise HTTPException(status_code=r.status_code, detail=r.text)
                data = r.json()
                data["routed_to"]     = "models-v1"
                data["model_version"] = "v1"
                data["ensemble_version"] = "v1"
                data["ensemble_info"] = {
                    "note": (
                        "Classic lightweight models — academic baseline. "
                        "Uses heuristic analysis without deep learning training."
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
    """Upload file to Analysis Service (stores in MinIO, creates DB record)."""
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
            raise HTTPException(status_code=503, detail="Analysis service unreachable")


@app.get("/api/status/{analysis_id}")
async def get_status(
    analysis_id:   str,
    authorization: Optional[str] = Header(None)
):
    """Get analysis job status from Analysis Service."""
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
            raise HTTPException(status_code=503, detail="Analysis service unreachable")


# ─────────────────────────────────────────────────────────────────────────────
# Auth passthrough
# ─────────────────────────────────────────────────────────────────────────────

@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(path: str, request: Request):
    """Proxy all /auth/* requests to Auth Service."""
    body    = await request.body()
    headers = dict(request.headers)
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