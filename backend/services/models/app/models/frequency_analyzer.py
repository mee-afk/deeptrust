"""
Frequency Domain Analyzer
Detects deepfakes using FFT and DCT analysis.
Deepfakes often have frequency anomalies invisible to naked eye.
"""
import numpy as np
from scipy import fftpack
from PIL import Image
import cv2
import logging

logger = logging.getLogger(__name__)


class FrequencyAnalyzer:
    """
    Frequency-based deepfake detection.
    
    Methods:
    - FFT (Fast Fourier Transform) - detects periodic artifacts
    - DCT (Discrete Cosine Transform) - JPEG compression artifacts
    
    Deepfakes often show:
    - Abnormal high-frequency patterns
    - Compression artifact inconsistencies
    - Unnatural frequency distributions
    """
    
    def __init__(self):
        logger.info("✅ Frequency Analyzer initialized")
    
    def analyze_fft(self, image):
        """
        FFT analysis for periodic artifacts.
        
        Returns:
            Anomaly score [0-1]
        """
        if isinstance(image, Image.Image):
            image = np.array(image.convert('L'))  # Grayscale
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Compute 2D FFT
        fft = np.fft.fft2(image)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        
        # Analyze high-frequency content
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        
        # High-frequency region (outer 20%)
        mask = np.ones((h, w), dtype=bool)
        mask[int(h * 0.4):int(h * 0.6), int(w * 0.4):int(w * 0.6)] = False
        
        high_freq_power = np.mean(magnitude[mask])
        total_power = np.mean(magnitude)
        
        # Calculate ratio
        hf_ratio = high_freq_power / (total_power + 1e-10)
        
        # Normalize to [0, 1] - higher ratio = more suspicious
        anomaly_score = min(hf_ratio * 2, 1.0)
        
        return float(anomaly_score)
    
    def analyze_dct(self, image):
        """
        DCT analysis for compression artifacts.
        
        Returns:
            Anomaly score [0-1]
        """
        if isinstance(image, Image.Image):
            image = np.array(image.convert('L'))
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Compute 2D DCT
        dct = fftpack.dct(fftpack.dct(image.T, norm='ortho').T, norm='ortho')
        
        # Analyze DCT coefficient distribution
        abs_dct = np.abs(dct)
        
        # High-frequency DCT coefficients (bottom-right quadrant)
        h, w = abs_dct.shape
        hf_coeffs = abs_dct[h//2:, w//2:]
        
        # Calculate entropy of high-frequency coefficients
        hf_mean = np.mean(hf_coeffs)
        hf_std = np.std(hf_coeffs)
        
        # Abnormally high variance indicates artifacts
        cv = hf_std / (hf_mean + 1e-10)  # Coefficient of variation
        
        # Normalize
        anomaly_score = min(cv / 10, 1.0)
        
        return float(anomaly_score)
    
    def predict(self, image):
        """
        Combined frequency analysis.
        
        Args:
            image: PIL Image or numpy array
            
        Returns:
            dict with 'score' (0-1) and 'is_fake' (bool)
        """
        try:
            fft_score = self.analyze_fft(image)
            dct_score = self.analyze_dct(image)
            
            # Weighted average
            combined_score = (fft_score * 0.6 + dct_score * 0.4)
            
            return {
                'score': float(combined_score),
                'is_fake': bool(combined_score > 0.5),
                'confidence': float(abs(combined_score - 0.5) * 2),
                'fft_anomaly': float(fft_score),
                'dct_anomaly': float(dct_score)
            }
        except Exception as e:
            logger.error(f"❌ Frequency analysis failed: {e}")
            return {
                'score': 0.5,
                'is_fake': False,
                'confidence': 0.0,
                'error': str(e)
            }