"""
DeepTrust Models Service
Deepfake detection ML models API.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import os
import logging

# Initialize models
from app.models.mesonet import MesoNet
from app.models.xception import XceptionNet
from app.models.frequency_analyzer import FrequencyAnalyzer
from app.models.biological_analyzer import BiologicalAnalyzer
from app.models.ensemble import EnsembleDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepTrust Models Service",
    description="ML models for deepfake detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global model instances
mesonet = None
xception = None
frequency = None
biological = None
ensemble = None


@app.on_event("startup")
async def startup():
    global mesonet, xception, frequency, biological, ensemble
    
    print("🚀 Starting Models Service...")
    print("📦 Loading ML models...")
    
    try:
        # Initialize all models
        mesonet = MesoNet()
        xception = XceptionNet()
        frequency = FrequencyAnalyzer()
        biological = BiologicalAnalyzer()
        
        # Create ensemble
        ensemble = EnsembleDetector(mesonet, xception, frequency, biological)
        
        print("✅ All models loaded successfully")
        
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        raise


@app.get("/")
async def root():
    return {
        "message": "DeepTrust Models Service",
        "version": "1.0.0",
        "models": ["MesoNet", "XceptionNet", "Frequency", "Biological"],
        "endpoints": {
            "predict": "/predict",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    models_loaded = all([mesonet, xception, frequency, biological, ensemble])
    
    return {
        "status": "healthy" if models_loaded else "degraded",
        "service": "models",
        "version": "1.0.0",
        "models_loaded": models_loaded,
        "available_models": {
            "mesonet": mesonet is not None,
            "xception": xception is not None,
            "frequency": frequency is not None,
            "biological": biological is not None,
            "ensemble": ensemble is not None
        }
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Predict if uploaded image/video is a deepfake.
    
    Returns complete ensemble analysis with all model predictions.
    """
    if not ensemble:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # Read uploaded file
        contents = await file.read()
        
        # Open as PIL Image
        image = Image.open(io.BytesIO(contents))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        logger.info(f"🔍 Analyzing {file.filename} ({image.size})")
        
        # Run ensemble prediction
        result = ensemble.predict(image)
        
        # Add metadata
        result['file_info'] = {
            'filename': file.filename,
            'size': len(contents),
            'dimensions': image.size,
            'format': image.format
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/predict/mesonet")
async def predict_mesonet(file: UploadFile = File(...)):
    """MesoNet only prediction"""
    if not mesonet:
        raise HTTPException(status_code=503, detail="MesoNet not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = mesonet.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/xception")
async def predict_xception(file: UploadFile = File(...)):
    """XceptionNet only prediction"""
    if not xception:
        raise HTTPException(status_code=503, detail="XceptionNet not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = xception.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/frequency")
async def predict_frequency(file: UploadFile = File(...)):
    """Frequency analysis only"""
    if not frequency:
        raise HTTPException(status_code=503, detail="Frequency analyzer not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = frequency.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/biological")
async def predict_biological(file: UploadFile = File(...)):
    """Biological analysis only"""
    if not biological:
        raise HTTPException(status_code=503, detail="Biological analyzer not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = biological.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)