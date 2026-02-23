"""
MesoNet - Simplified Deepfake Detection
Lightweight version using statistical analysis instead of CNN.
"""
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class MesoNet:
    """
    Simplified MesoNet for deepfake detection.
    Uses texture and compression artifact analysis.
    """
    
    def __init__(self, input_shape=(256, 256, 3)):
        self.input_shape = input_shape
        logger.info("✅ MesoNet (Lightweight) initialized")
    
    def preprocess(self, image):
        """Preprocess image"""
        if hasattr(image, 'resize'):
            image = image.resize((256, 256))
            image = np.array(image)
        
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[-1] == 4:
            image = image[:, :, :3]
        
        image = image.astype(np.float32) / 255.0
        return image
    
    def predict(self, image):
        """
        Detect deepfakes using texture analysis.
        """
        try:
            preprocessed = self.preprocess(image)
            
            # Analyze texture variance
            gray = np.mean(preprocessed, axis=2)
            variance = np.var(gray)
            
            # Analyze edge sharpness
            edges_h = np.abs(np.diff(gray, axis=0))
            edges_v = np.abs(np.diff(gray, axis=1))
            edge_strength = np.mean(edges_h) + np.mean(edges_v)
            
            # Combine metrics
            texture_score = 1.0 - min(variance * 10, 1.0)
            edge_score = 1.0 - min(edge_strength * 5, 1.0)
            
            score = (texture_score * 0.6 + edge_score * 0.4)
            
            return {
                'score': float(score),
                'is_fake': bool(score > 0.5),
                'confidence': float(abs(score - 0.5) * 2)
            }
        except Exception as e:
            logger.error(f"❌ MesoNet prediction failed: {e}")
            return {
                'score': 0.5,
                'is_fake': False,
                'confidence': 0.0,
                'error': str(e)
            }
