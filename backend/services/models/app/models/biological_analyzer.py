"""
Biological Signal Analyzer
==========================
This module implements deepfake detection by analyzing physiological and biological 
consistency. It focuses on features that are traditionally difficult for generative 
adversarial networks (GANs) to replicate correctly, such as eye blinking patterns 
and natural facial asymmetry.
"""

import numpy as np
import cv2
from PIL import Image
import logging

# Configure logger for biological consistency diagnostics
logger = logging.getLogger(__name__)


class BiologicalAnalyzer:
    """
    Biological signal analysis for deepfake detection.
    
    This detector provides a sanity check on the human aspect of the face, analyzing:
    - Facial Symmetry: Real faces are naturally asymmetric; high-degree mathematical 
      symmetry can indicate synthetic rendering.
    - Eye Texture & Consistency: Analyzes the variation and rendering of the iris 
      and sclera to find uniform or 'painted-on' textures.
    """
    
    def __init__(self):
        """
        Initializes the biological analyzer.
        Loads pre-trained Haar cascades for facial and ocular feature detection.
        """
        # Load OpenCV's standard cascade classifiers
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        logger.info("✅ Biological Analyzer initialized")
    
    def detect_face_symmetry(self, image):
        """
        Analyzes bilateral facial symmetry.
        
        Deepfakes, especially those based on average-face models, often exhibit 
        unnatural perfection in symmetry. Real human faces show subtle differences 
        between the left and right hemispheres.
        
        Args:
            image: PIL Image or numpy array.
            
        Returns:
            Symmetry score [0-1] - higher = more symmetric = more suspicious
        """
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Convert to grayscale for structural similarity analysis
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Isolate the face region for precise comparison
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return 0.5  # No face detected, neutral score
        
        # Take first detected face
        (x, y, w, h) = faces[0]
        face = gray[y:y+h, x:x+w]
        
        # Split face vertically
        mid = w // 2
        left_half = face[:, :mid]
        right_half = cv2.flip(face[:, mid:], 1)  # Flip right half
        
        # Resize to same dimensions
        min_width = min(left_half.shape[1], right_half.shape[1])
        left_half = cv2.resize(left_half, (min_width, face.shape[0]))
        right_half = cv2.resize(right_half, (min_width, face.shape[0]))
        
        # Calculate similarity (MSE)
        mse = np.mean((left_half.astype(float) - right_half.astype(float)) ** 2)
        
        # Normalize - perfect symmetry (low MSE) is suspicious
        # Natural faces have some asymmetry
        symmetry_score = 1.0 / (1.0 + mse / 1000.0)
        
        return float(symmetry_score)
    
    def detect_eye_patterns(self, image):
        """
        Analyze eye patterns.
        Deepfakes often have unnatural eye rendering.
            
        Returns:
            Anomaly score [0-1]
        """
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Detect eyes
        eyes = self.eye_cascade.detectMultiScale(gray, 1.1, 3)
        
        if len(eyes) < 2:
            return 0.5  # Need at least 2 eyes
        
        eye_scores = []
        for (ex, ey, ew, eh) in eyes[:2]:
            eye_region = gray[ey:ey+eh, ex:ex+ew]
            
            # Analyze texture variance in the eye region.
            # Real eyes have complex reflections and textures (high variance).
            # Deepfakes often have 'smooth' or unnaturally uniform eyes (low variance).
            variance = np.var(eye_region)
            
            # Low variance translates to a higher suspiciousness score.
            eye_scores.append(1.0 / (1.0 + variance / 100.0))
        
        return float(np.mean(eye_scores))
    
    def predict(self, image) -> dict:
        """
        Executes a holistic biological evaluation of the input image.
        
        Args:
            image: PIL Image or numpy array.
            
        Returns:
            dict: Aggregated biological markers and final verdict.
        """
        try:
            # Measure symmetry and ocular markers
            symmetry_score = self.detect_face_symmetry(image)
            eye_score = self.detect_eye_patterns(image)
            
            # Weighted aggregation: 
            # 60% weight on facial symmetry markers, 40% on eye rendering artifacts.
            combined_score = (symmetry_score * 0.6 + eye_score * 0.4)
            
            return {
                'score': float(combined_score),
                'is_fake': bool(combined_score > 0.5),
                'confidence': float(abs(combined_score - 0.5) * 2),
                'symmetry_score': float(symmetry_score),
                'eye_anomaly': float(eye_score)
            }
        except Exception as e:
            logger.error(f"Critical execution failure in Biological Analyzer: {e}")
            return {
                'score': 0.5,
                'is_fake': False,
                'confidence': 0.0,
                'error': f"Biological analyzer engine failure: {str(e)}"
            }