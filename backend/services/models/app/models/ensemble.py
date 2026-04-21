"""
Ensemble Detection Engine
=========================
This module implements the EnsembleDetector class, which aggregates predictions 
from multiple sub-models to provide a more robust and reliable deepfake detection verdict.
The ensemble uses a weighted scoring mechanism based on the known performance and 
specialization of each underlying model.
"""

import numpy as np
import logging
from typing import Dict, Any
from PIL import Image

# Setup logger for the ensemble engine
logger = logging.getLogger(__name__)


class EnsembleDetector:
    """
    Ensemble deepfake detection system.
    
    This class orchestrates the inference process across four specialized models:
    - MesoNet (30% weight): Focuses on meso-layer texture analysis and compression artifacts.
    - XceptionNet (35% weight): High-capacity CNN for capturing deep semantic facial features.
    - Frequency Analyzer (20% weight): Statistically analyzes high-frequency spectral noise.
    - Biological Analyzer (15% weight): Checks for biological inconsistencies like blinking or facial symmetry.
    
    The final decision is reached by calculating a weighted average of model confidence scores.
    """
    
    def __init__(self, mesonet, xception, frequency, biological):
        """
        Initialize the ensemble with pre-loaded model instances.
        
        Args:
            mesonet: An initialized MesoNet model instance.
            xception: An initialized XceptionNet model instance.
            frequency: An initialized FrequencyAnalyzer instance.
            biological: An initialized BiologicalAnalyzer instance.
        """
        self.mesonet = mesonet
        self.xception = xception
        self.frequency = frequency
        self.biological = biological
        
        # Model weights reflecting relative importance/confidence in each detector's accuracy.
        # These weights are tuned to sum to 1.0.
        self.weights = {
            'mesonet': 0.30,
            'xception': 0.35,
            'frequency': 0.20,
            'biological': 0.15
        }
        
        logger.info("Ensemble Detector successfully initialized")
        logger.info(f"Active Ensemble Configuration Weights: {self.weights}")
    
    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """
        Executes a consensus prediction on a single input image.
        
        This method triggers inference on all sub-models, aggregates their results,
        and computes a final probability score and binary verdict.
        
        Args:
            image (PIL.Image.Image): The pre-processed input image containing a human face.
            
        Returns:
            Dict[str, Any]: A comprehensive analysis response including:
                - is_deepfake: Final boolean verdict.
                - confidence_score: Estimated certainty (0 to 1).
                - ensemble_score: Combined probability of the image being a deepfake.
                - model_scores: Breakdown of raw scores from each individual model.
                - voting: Summary of binary votes from the sub-models.
                - model_details: Full raw output from each sub-model for deeper inspection.
        """
        try:
            logger.info("Initiating ensemble inference sequence...")
            
            # Run inference across all specialized models.
            # While these run sequentially here, the results are captured for aggregation.
            mesonet_result = self.mesonet.predict(image)
            xception_result = self.xception.predict(image)
            frequency_result = self.frequency.predict(image)
            biological_result = self.biological.predict(image)
            
            # Consolidate raw probability scores from all detectors.
            scores = {
                'mesonet': mesonet_result['score'],
                'xception': xception_result['score'],
                'frequency': frequency_result['score'],
                'biological': biological_result['score']
            }
            
            # Calculate the aggregate ensemble score using the predefined weights.
            # An ensemble score closer to 1.0 indicates a high probability of a deepfake.
            ensemble_score = (
                scores['mesonet'] * self.weights['mesonet'] +
                scores['xception'] * self.weights['xception'] +
                scores['frequency'] * self.weights['frequency'] +
                scores['biological'] * self.weights['biological']
            )
            
            # Final binary decision based on a 0.5 threshold.
            is_deepfake = ensemble_score > 0.5
            
            # Normalized confidence calculation: maps the distance from the decision boundary to [0, 1].
            confidence = abs(ensemble_score - 0.5) * 2
            
            # Aggregate binary votes from all models for internal cross-validation.
            votes = {
                'mesonet': mesonet_result['is_fake'],
                'xception': xception_result['is_fake'],
                'frequency': frequency_result['is_fake'],
                'biological': biological_result['is_fake']
            }
            
            votes_fake = sum(votes.values())
            votes_real = len(votes) - votes_fake
            
            # Build the finalized result payload.
            result = {
                'is_deepfake': bool(is_deepfake),
                'confidence_score': float(confidence),
                'ensemble_score': float(ensemble_score),
                
                # Distribution of scores across the ensemble.
                'model_scores': {
                    'mesonet': float(scores['mesonet']),
                    'xception': float(scores['xception']),
                    'frequency': float(scores['frequency']),
                    'biological': float(scores['biological'])
                },
                
                # Breakdown of model consensus.
                'voting': {
                    'fake_votes': int(votes_fake),
                    'real_votes': int(votes_real),
                    'individual_votes': votes
                },
                
                # Metadata on the weighting algorithm used.
                'ensemble_weights': self.weights,
                
                # Passthrough of full model diagnostics for external XAI services or debugging.
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
                'error': f"Internal ensemble error: {str(e)}"
            }