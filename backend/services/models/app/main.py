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
    
    logger.info("Starting Models Service...")
    logger.info("Loading ML models...")
    
    try:
        # Initialize all models
        mesonet = MesoNet()
        xception = XceptionNet()
        frequency = FrequencyAnalyzer()
        biological = BiologicalAnalyzer()
        
        # Create ensemble
        ensemble = EnsembleDetector(mesonet, xception, frequency, biological)
        
        logger.info("All models loaded successfully")
        
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
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
    """Predict if uploaded image/video is a deepfake."""
    if not ensemble:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        logger.info(f"🔍 Analyzing {file.filename} ({image.size})")
        
        # Face validation with error handling
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                logger.warning(f"⚠️ No face detected in {file.filename}")
                return {
                    "is_deepfake": False,
                    "confidence_score": 0.0,
                    "ensemble_score": 0.5,
                    "error": "no_face_detected",
                    "message": "No human face detected in image. Results may be unreliable.",
                    "model_scores": {
                        "mesonet": 0.5,
                        "xception": 0.5,
                        "frequency": 0.5,
                        "biological": 0.5
                    },
                    "voting": {
                        "fake_votes": 0,
                        "real_votes": 0
                    },
                    "ensemble_weights": {
                        "mesonet": 0.3,
                        "xception": 0.35,
                        "frequency": 0.2,
                        "biological": 0.15
                    },
                    "file_info": {
                        "filename": file.filename,
                        "size": len(contents),
                        "dimensions": image.size,
                        "format": image.format
                    }
                }
            
            logger.info(f"✅ Detected {len(faces)} face(s)")
        except Exception as face_error:
            logger.warning(f"⚠️ Face detection failed: {face_error}, continuing anyway...")
        
        # Run ensemble prediction
        result = ensemble.predict(image)
        
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