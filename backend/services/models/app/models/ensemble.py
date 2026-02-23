"""
Ensemble Detection Engine
Combines predictions from multiple models using weighted voting.
"""
import numpy as np
import logging
from typing import Dict, Any
from PIL import Image

logger = logging.getLogger(__name__)


class EnsembleDetector:
    """
    Ensemble deepfake detection system.
    
    Combines 4 models:
    - MesoNet (30% weight) - Fast CNN
    - XceptionNet (35% weight) - Powerful CNN
    - Frequency Analyzer (20% weight) - FFT/DCT
    - Biological Analyzer (15% weight) - Blink/symmetry
    
    Decision: Weighted voting with confidence scores
    """
    
    def __init__(self, mesonet, xception, frequency, biological):
        self.mesonet = mesonet
        self.xception = xception
        self.frequency = frequency
        self.biological = biological
        
        # Model weights (must sum to 1.0)
        self.weights = {
            'mesonet': 0.30,
            'xception': 0.35,
            'frequency': 0.20,
            'biological': 0.15
        }
        
        logger.info("✅ Ensemble Detector initialized")
        logger.info(f"   Weights: {self.weights}")
    
    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """
        Run ensemble prediction on image.
        
        Args:
            image: PIL Image
            
        Returns:
            Complete analysis with all model predictions
        """
        try:
            logger.info("🔍 Running ensemble detection...")
            
            # Run all models in parallel
            mesonet_result = self.mesonet.predict(image)
            xception_result = self.xception.predict(image)
            frequency_result = self.frequency.predict(image)
            biological_result = self.biological.predict(image)
            
            # Extract scores
            scores = {
                'mesonet': mesonet_result['score'],
                'xception': xception_result['score'],
                'frequency': frequency_result['score'],
                'biological': biological_result['score']
            }
            
            # Calculate weighted ensemble score
            ensemble_score = (
                scores['mesonet'] * self.weights['mesonet'] +
                scores['xception'] * self.weights['xception'] +
                scores['frequency'] * self.weights['frequency'] +
                scores['biological'] * self.weights['biological']
            )
            
            # Final decision
            is_deepfake = ensemble_score > 0.5
            confidence = abs(ensemble_score - 0.5) * 2  # 0-1 scale
            
            # Voting breakdown
            votes = {
                'mesonet': mesonet_result['is_fake'],
                'xception': xception_result['is_fake'],
                'frequency': frequency_result['is_fake'],
                'biological': biological_result['is_fake']
            }
            
            votes_fake = sum(votes.values())
            votes_real = len(votes) - votes_fake
            
            result = {
                'is_deepfake': bool(is_deepfake),
                'confidence_score': float(confidence),
                'ensemble_score': float(ensemble_score),
                
                # Individual model scores
                'model_scores': {
                    'mesonet': float(scores['mesonet']),
                    'xception': float(scores['xception']),
                    'frequency': float(scores['frequency']),
                    'biological': float(scores['biological'])
                },
                
                # Voting breakdown
                'voting': {
                    'fake_votes': int(votes_fake),
                    'real_votes': int(votes_real),
                    'individual_votes': votes
                },
                
                # Weights used
                'ensemble_weights': self.weights,
                
                # Detailed model outputs
                'model_details': {
                    'mesonet': mesonet_result,
                    'xception': xception_result,
                    'frequency': frequency_result,
                    'biological': biological_result
                }
            }
            
            verdict = "DEEPFAKE" if is_deepfake else "AUTHENTIC"
            logger.info(f"✅ Ensemble verdict: {verdict} ({confidence:.2%} confidence)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ensemble prediction failed: {e}")
            return {
                'is_deepfake': False,
                'confidence_score': 0.0,
                'ensemble_score': 0.5,
                'error': str(e)
            }