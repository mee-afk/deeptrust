"""
Frequency Domain Analyzer
=========================
This module detects deepfakes by analyzing the frequency domain of images. 
Generative models often leave subtle 'spectral fingerprints' or high-frequency 
anomalies that are invisible to the naked eye but distinguishable in the 
Fourier or DCT spectrum.
"""

import numpy as np
from scipy import fftpack
from PIL import Image
import cv2
import logging

# Configure logger for spectral analysis diagnostics
logger = logging.getLogger(__name__)


class FrequencyAnalyzer:
    """
    Frequency-based deepfake detection system.
    
    This class implements two primary spectral analysis methods:
    1. FFT (Fast Fourier Transform): Detects periodic grid artifacts or 'checkerboard' 
       patterns often caused by upsampling in GANs.
    2. DCT (Discrete Cosine Transform): Identifies inconsistencies in JPEG-like 
       compression artifacts and high-frequency noise distributions.
    """
    
    def __init__(self):
        """Initializes the Frequency Analyzer engine."""
        logger.info("Frequency Analyzer spectral engine ready")
    
    def analyze_fft(self, image):
        """
        Performs 2D Fast Fourier Transform to analyze periodic artifacts.
        
        Analyzes the ratio of high-frequency power to total spectral power. 
        Unnatural high-frequency energy levels often indicate synthetic generation.
        
        Args:
            image: PIL Image or numpy array representing the face frame.
            
        Returns:
            float: Anomaly score ranging from 0.0 (likely real) to 1.0 (highly suspicious).
        """
        # Standardize input to grayscale numpy array
        if isinstance(image, Image.Image):
            image = np.array(image.convert('L'))  # Grayscale
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Compute the 2D FFT and shift zero-frequency component to the center
        fft = np.fft.fft2(image)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        
        # Determine the high-frequency boundaries (outer 20% of the spectrum)
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        
        # High-frequency region (outer 20%)
        mask = np.ones((h, w), dtype=bool)
        # Exclude the low-frequency center (DC component and surroundings)
        mask[int(h * 0.4):int(h * 0.6), int(w * 0.4):int(w * 0.6)] = False
        
        high_freq_power = np.mean(magnitude[mask])
        total_power = np.mean(magnitude)
        
        # Calculate the high-frequency energy ratio. 
        # A significant shift towards higher frequencies can indicate generative noise.
        hf_ratio = high_freq_power / (total_power + 1e-10)
        
        # Normalize the ratio based on typical atmospheric/sensor noise baselines.
        anomaly_score = min(hf_ratio * 2, 1.0)
        
        return float(anomaly_score)
    
    def analyze_dct(self, image):
        """
        Performs 2D Discrete Cosine Transform for compression artifact analysis.
        
        Analyzes coefficient entropy in the high-frequency DCT spectrum. 
        Abnormal variance in the bottom-right quadrant of the DCT block often 
        correlates with synthetic reconstruction artifacts.
        
        Args:
            image: PIL Image or numpy array.
            
        Returns:
            Anomaly score [0-1]
        """
        # Standardize input to grayscale
        if isinstance(image, Image.Image):
            image = np.array(image.convert('L'))
        elif len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Compute 2D DCT using orthogonal normalization
        dct = fftpack.dct(fftpack.dct(image.T, norm='ortho').T, norm='ortho')
        
        # Isolate the high-frequency coefficients (typically the bottom-right quadrant)
        abs_dct = np.abs(dct)
        h, w = abs_dct.shape
        hf_coeffs = abs_dct[h//2:, w//2:]
        
        # Measure the Coefficient of Variation (CV) of high-frequency components.
        # Natural faces show predictable decay in DCT coefficients; 
        # deepfakes often show 'noisy' or irregular high-frequency coefficients.
        hf_mean = np.mean(hf_coeffs)
        hf_std = np.std(hf_coeffs)
        
        # Abnormally high variance indicates artifacts
        cv = hf_std / (hf_mean + 1e-10)  # Coefficient of variation
        
        # Normalize the variance to a probability-like score.
        anomaly_score = min(cv / 10, 1.0)
        
        return float(anomaly_score)
    
    def predict(self, image):
        """
        Aggregates FFT and DCT analysis for a unified frequency domain verdict.
        
        Args:
            image: PIL Image or numpy array.
            
        Returns:
            dict: Comprehensive results including combined score and individual anomalies.
        """
        try:
            # Execute individual spectral analyzers
            fft_score = self.analyze_fft(image)
            dct_score = self.analyze_dct(image)
            
            # Combine scores with specific domain weights: 
            # 60% weight on periodic FFT artifacts, 40% on DCT compression artifacts.
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