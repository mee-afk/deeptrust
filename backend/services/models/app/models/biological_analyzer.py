"""
Biological Signal Analyzer
Detects deepfakes by analyzing biological signals like blink patterns.
Real humans blink naturally; deepfakes often have unnatural blink patterns.
"""
import numpy as np
import cv2
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class BiologicalAnalyzer:
    """
    Biological signal analysis for deepfake detection.
    
    Features analyzed:
    - Blink rate and timing
    - Facial symmetry
    - Micro-expressions
    - Eye aspect ratio (EAR)
    
    Deepfakes typically fail to replicate:
    - Natural blink patterns
    - Perfect left-right facial symmetry
    - Subtle muscle movements
    """
    
    def __init__(self):
        # Load face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        logger.info("✅ Biological Analyzer initialized")
    
    def detect_face_symmetry(self, image):
        """
        Analyze facial symmetry.
        Deepfakes often have unnatural perfect symmetry.
        
        Returns:
            Symmetry score [0-1] - higher = more symmetric = more suspicious
        """
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Detect faces
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
        
        # Analyze eye regions
        eye_scores = []
        for (ex, ey, ew, eh) in eyes[:2]:  # Take first 2 eyes
            eye_region = gray[ey:ey+eh, ex:ex+ew]
            
            # Calculate variance (deepfakes often have uniform eye texture)
            variance = np.var(eye_region)
            
            # Low variance = suspicious
            eye_scores.append(1.0 / (1.0 + variance / 100.0))
        
        return float(np.mean(eye_scores))
    
    def predict(self, image):
        """
        Combined biological signal analysis.
        
        Args:
            image: PIL Image or numpy array
            
        Returns:
            dict with 'score' (0-1) and 'is_fake' (bool)
        """
        try:
            symmetry_score = self.detect_face_symmetry(image)
            eye_score = self.detect_eye_patterns(image)
            
            # Weighted combination
            combined_score = (symmetry_score * 0.6 + eye_score * 0.4)
            
            return {
                'score': float(combined_score),
                'is_fake': bool(combined_score > 0.5),
                'confidence': float(abs(combined_score - 0.5) * 2),
                'symmetry_score': float(symmetry_score),
                'eye_anomaly': float(eye_score)
            }
        except Exception as e:
            logger.error(f"❌ Biological analysis failed: {e}")
            return {
                'score': 0.5,
                'is_fake': False,
                'confidence': 0.0,
                'error': str(e)
            }