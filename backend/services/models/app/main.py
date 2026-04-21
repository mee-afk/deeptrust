"""
DeepTrust Models Service
========================
This service provides an API for multiple machine learning models used in deepfake detection.
It includes traditional forensic analyzers and modern convolutional network models,
coordinated through an EnsembleDetector.
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

# Configure logging for service monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepTrust Models Service",
    description="Machine Learning models and ensemble detector for deepfake identification.",
    version="1.0.0"
)

# Configure CORS to allow communication from the API Gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global instances of ML models. Initialized on startup to ensure availability for inference.
mesonet = None
xception = None
frequency = None
biological = None
ensemble = None


@app.on_event("startup")
async def startup():
    """
    Service startup event handler.
    Initializes and loads weights for all deepfake detection models into memory.
    """
    global mesonet, xception, frequency, biological, ensemble
    
    logger.info("Starting Models Service...")
    logger.info("Loading ML models into memory...")
    
    try:
        # Instantiate each model. Weight loading typically occurs within the constructor.
        mesonet = MesoNet()
        xception = XceptionNet()
        frequency = FrequencyAnalyzer()
        biological = BiologicalAnalyzer()
        
        # Create an ensemble that aggregates results from the individual models
        ensemble = EnsembleDetector(mesonet, xception, frequency, biological)
        
        logger.info("All models loaded successfully and ready for inference")
        
    except Exception as e:
        logger.error(f"Critical failure during model initialization: {e}")
        # Raising an exception here prevents the service from starting in an unhealthy state
        raise


@app.get("/")
async def root():
    """
    Service information endpoint.
    Returns basic metadata and available endpoints for discovery.
    """
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
    """
    Health check endpoint.
    Verifies that all required models are successfully loaded and the service is operational.
    """
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
    Main prediction endpoint using the ensemble detector.
    
    Args:
        file (UploadFile): The image or frame extracted from a video for analysis.
        
    Returns:
        dict: A structured dictionary containing the deepfake detection verdict, 
              confidence scores, and individual model breakdowns.
        
    Raises:
        HTTPException: 503 if models are not loaded, or 500 if inference fails.
    """
    if not ensemble:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # Read file contents and convert to a PIL Image for model processing
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Ensure image is in RGB format, required by most CNN architectures
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        logger.info(f"🔍 Analyzing {file.filename} ({image.size})")
        
        # Optional: Face validation using OpenCV's Haar Cascades
        # This provides an early exit or warning if no human face is detected.
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
                logger.warning(f"No face detected in {file.filename}")
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
            # Face detection is a non-blocking enhancement; failures are logged but inference continues
            logger.warning(f"⚠️ Face detection module failure: {face_error}, proceeding with inference...")
        
        # Run consensus prediction across all loaded models
        result = ensemble.predict(image)
        
        # Attach telemetry data about the analyzed file to the response
        result['file_info'] = {
            'filename': file.filename,
            'size': len(contents),
            'dimensions': image.size,
            'format': image.format
        }
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Prediction engine failure for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Inference engine failure: {str(e)}")


@app.post("/predict/mesonet")
async def predict_mesonet(file: UploadFile = File(...)):
    """
    Isolated measurement endpoint for MesoNet analysis.
    Useful for research evaluation of texture-based detection.
    """
    if not mesonet:
        raise HTTPException(status_code=503, detail="MesoNet not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = mesonet.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MesoNet execution error: {str(e)}")


@app.post("/predict/xception")
async def predict_xception(file: UploadFile = File(...)):
    """
    Isolated measurement endpoint for XceptionNet analysis.
    Provides deep semantic feature analysis of the input image.
    """
    if not xception:
        raise HTTPException(status_code=503, detail="XceptionNet not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = xception.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XceptionNet execution error: {str(e)}")


@app.post("/predict/frequency")
async def predict_frequency(file: UploadFile = File(...)):
    """
    Isolated measurement endpoint for Frequency Domain analysis.
    Identifies high-frequency spectral artifacts characteristic of generative models.
    """
    if not frequency:
        raise HTTPException(status_code=503, detail="Frequency analyzer not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = frequency.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frequency analyzer execution error: {str(e)}")


@app.post("/predict/biological")
async def predict_biological(file: UploadFile = File(...)):
    """
    Isolated measurement endpoint for Biological Consistency analysis.
    Checks for anatomic and physiological markers that distinguish real from synthetic faces.
    """
    if not biological:
        raise HTTPException(status_code=503, detail="Biological analyzer not loaded")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        result = biological.predict(image)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Biological analyzer execution error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Local development server entry point
    uvicorn.run(app, host="0.0.0.0", port=8003)