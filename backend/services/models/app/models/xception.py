"""
XceptionNet - Simplified Deepfake Detection
Lightweight version using HOG features.
"""
import numpy as np
from PIL import Image
from skimage.feature import hog
import logging

logger = logging.getLogger(__name__)


class XceptionNet:
    """Simplified XceptionNet using feature extraction."""
    
    def __init__(self, input_shape=(299, 299, 3)):
        self.input_shape = input_shape
        logger.info("✅ XceptionNet (Lightweight) initialized")
    
    def preprocess(self, image):
        """Preprocess image"""
        if hasattr(image, 'resize'):
            image = image.resize((299, 299))
            image = np.array(image)
        
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[-1] == 4:
            image = image[:, :, :3]
        
        image = image.astype(np.float32) / 255.0
        return image
    
    def predict(self, image):
        """Detect deepfakes using HOG features."""
        try:
            preprocessed = self.preprocess(image)
            gray = np.mean(preprocessed, axis=2)
            
            # Extract HOG features
            features = hog(
                gray,
                orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                visualize=False
            )
            
            # Analyze feature distribution
            feature_variance = np.var(features)
            anomaly_score = min(abs(feature_variance - 0.02) * 20, 1.0)
            
            return {
                'score': float(anomaly_score),
                'is_fake': bool(anomaly_score > 0.5),
                'confidence': float(abs(anomaly_score - 0.5) * 2)
            }
        except Exception as e:
            logger.error(f"❌ XceptionNet prediction failed: {e}")
            return {
                'score': 0.5,
                'is_fake': False,
                'confidence': 0.0,
                'error': str(e)
            }
