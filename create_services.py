import os

auth_content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Auth Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth"}

@app.get("/")
async def root():
    return {"message": "Auth Service Running"}
"""

analysis_content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Analysis Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "analysis"}

@app.get("/")
async def root():
    return {"message": "Analysis Service Running"}
"""

models_content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Models Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "models"}

@app.get("/")
async def root():
    return {"message": "Models Service Running"}
"""

gateway_content = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DeepTrust API Gateway", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway", "version": "1.0.0"}

@app.get("/")
async def root():
    return {"message": "DeepTrust API Gateway", "docs": "/docs"}
"""

# Write files
os.makedirs('backend/services/auth/app', exist_ok=True)
os.makedirs('backend/services/analysis/app', exist_ok=True)
os.makedirs('backend/services/models/app', exist_ok=True)
os.makedirs('backend/services/gateway/app', exist_ok=True)

with open('backend/services/auth/app/main.py', 'w', encoding='utf-8') as f:
    f.write(auth_content)

with open('backend/services/analysis/app/main.py', 'w', encoding='utf-8') as f:
    f.write(analysis_content)

with open('backend/services/models/app/main.py', 'w', encoding='utf-8') as f:
    f.write(models_content)

with open('backend/services/gateway/app/main.py', 'w', encoding='utf-8') as f:
    f.write(gateway_content)

print("All service files created successfully!")
print("Files created:")
print("- backend/services/auth/app/main.py")
print("- backend/services/analysis/app/main.py")
print("- backend/services/models/app/main.py")
print("- backend/services/gateway/app/main.py")
