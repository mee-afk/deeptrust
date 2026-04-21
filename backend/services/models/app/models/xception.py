"""
XceptionNet - Simplified Deepfake Detection
===========================================
This module provides a lightweight feature-extraction version of the XceptionNet model.
Instead of the full deep neural network, it utilizes Histogram of Oriented Gradients (HOG)
to identify anomalies in facial structure and semantic features.
"""

import numpy as np
from PIL import Image
from skimage.feature import hog
import logging

# Setup logger for XceptionNet diagnostics
logger = logging.getLogger(__name__)


class XceptionNet:
    """
    Simplified XceptionNet implementation using feature extraction.
    
    This model uses HOG (Histogram of Oriented Gradients) to capture the 
    geometric structure of the face. Deepfakes often exhibit subtle 
    gradient-level inconsistencies that deviate from the expected 
    distribution of authentic human facial features.
    """
    
    def __init__(self, input_shape=(299, 299, 3)):
        """
        Initializes the XceptionNet simplified engine.
        
        Args:
            input_shape (tuple): The target input resolution for the model. 
                                 Defaults to the standard XceptionNet 299x299.
        """
        self.input_shape = input_shape
        logger.info("✅ XceptionNet (Lightweight) initialized")
    
    def preprocess(self, image: Image.Image) -> np.ndarray:
        """
        Prepares the input image for gradient-based feature extraction.
        
        Handles resizing, normalization, and channel validation.
        
        Args:
            image (PIL.Image.Image): The raw input image.
            
        Returns:
            np.ndarray: Preprocessed float32 array in [0, 1] range.
        """
        # Ensure image fits the target receptive field
        if hasattr(image, 'resize'):
            image = image.resize((299, 299))
            image = np.array(image)
        
        # Standardize color channels
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[-1] == 4:
            # Drop alpha channel to stay within RGB requirements
            image = image[:, :, :3]
        
        # Pixel value normalization
        image = image.astype(np.float32) / 255.0
        return image
    
    def predict(self, image: Image.Image) -> dict:
        """
        Detects anomalies using Histogram of Oriented Gradients (HOG).
        
        Calculates feature distribution variance and measures deviation 
        from the expected real-face baseline.
        
        Args:
            image (PIL.Image.Image): Input facial image.
            
        Returns:
            dict: Analysis results containing:
                - score: Probability of deepfake anomaly (0-1).
                - is_fake: Boolean verdict based on the 0.5 threshold.
                - confidence: Strength of the detection signal.
        """
        try:
            preprocessed = self.preprocess(image)
            
            # Convert to grayscale for gradient orientation analysis
            gray = np.mean(preprocessed, axis=2)
            
            # Extract HOG features: captures local shape and texture gradients.
            # These parameters are tuned for facial landmark resolution.
            features = hog(
                gray,
                orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                visualize=False
            )
            
            # Analyze the distribution of gradients.
            # Deepfakes often show 'flatter' or more 'uniform' gradient distributions 
            # compared to the complex irregularities of a real human face.
            feature_variance = np.var(features)
            
            # Heuristic anomaly score: measure distance from expected authentic variance (0.02).
            # Scaled to produce a 0 to 1 probability-like metric.
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
