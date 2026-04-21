"""
MesoNet - Simplified Deepfake Detection
=======================================
This module provides a lightweight, heuristic-based version of the MesoNet model.
Unlike a traditional CNN, this implementation uses statistical texture analysis and 
edge-strength measurement to identify common artifacts found in synthetic facial images.
"""

import numpy as np
from PIL import Image
import logging

# Configure logger for MesoNet diagnostics
logger = logging.getLogger(__name__)


class MesoNet:
    """
    Simplified MesoNet for deepfake detection.
    
    This detector focuses on meso-level image features, specifically analyzing:
    1. Texture Variance: Detects unnatural smoothness or patterned noise.
    2. Edge Sharpness: Detects blurring or ringing artifacts around facial features 
       often caused by GAN-based blending.
    """
    
    def __init__(self, input_shape=(256, 256, 3)):
        """
        Initializes the MesoNet detector.
        
        Args:
            input_shape (tuple): Expected dimensions for input images. Defaults to (256, 256, 3).
        """
        self.input_shape = input_shape
        logger.info("✅ MesoNet (Lightweight) initialized")
    
    def preprocess(self, image: Image.Image) -> np.ndarray:
        """
        Prepares the input image for statistical analysis.
        
        Performs resizing, color space correction, and normalization.
        
        Args:
            image (PIL.Image.Image): Raw input image.
            
        Returns:
            np.ndarray: Preprocessed image as a float32 array in [0, 1] range.
        """
        # Ensure the image is at the target resolution
        if hasattr(image, 'resize'):
            image = image.resize((256, 256))
            image = np.array(image)
        
        # Handle grayscale vs color channel inconsistencies
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)
        elif image.shape[-1] == 4:
            # Drop alpha channel if present
            image = image[:, :, :3]
        
        # Normalize pixel values to standard range for ML processing
        image = image.astype(np.float32) / 255.0
        return image
    
    def predict(self, image):
        """
        Executes deepfake detection using statistical texture analysis.
        
        Calculates a score based on combined variance and edge strength metrics.
        
        Args:
            image (PIL.Image.Image): Input facial image.
            
        Returns:
            dict: Detection results containing:
                - score: Aggregate probability (0-1).
                - is_fake: Boolean verdict based on the 0.5 threshold.
                - confidence: Measured distance from the decision boundary.
        """
        try:
            preprocessed = self.preprocess(image)
            
            # Convert to luminance for statistical frequency analysis
            gray = np.mean(preprocessed, axis=2)
            
            # Metric 1: Texture Variance. 
            # High variance suggests natural skin texture; low variance can indicate GAN-smoothed regions.
            variance = np.var(gray)
            
            # Metric 2: Edge Sharpness.
            # Measures horizontal and vertical gradients to find unnatural blurring at blending boundaries.
            edges_h = np.abs(np.diff(gray, axis=0))
            edges_v = np.abs(np.diff(gray, axis=1))
            edge_strength = np.mean(edges_h) + np.mean(edges_v)
            
            # Combined Metric Normalization.
            # Heuristic weights: 60% texture variance, 40% edge strength.
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
