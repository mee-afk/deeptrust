from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DeepTrust API Gateway", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "DeepTrust API Gateway", "docs": "/docs"}
