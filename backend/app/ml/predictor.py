"""
MediTrack ML Predictor Service
Loads trained model, performs real-time feature extraction and probability calibration,
and augments predictions with AI clinical interventions.
"""
import os
import json
import joblib
from typing import Dict, Any, Optional
import pandas as pd

try:
    from app.ml.features import extract_features_single
    from app.ml.insights import generate_clinical_interventions
    from app.ml.trainer import ARTIFACT_PATH, METRICS_PATH, train_and_evaluate_model
except ImportError:
    try:
        from .features import extract_features_single
        from .insights import generate_clinical_interventions
        from .trainer import ARTIFACT_PATH, METRICS_PATH, train_and_evaluate_model
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from features import extract_features_single
        from insights import generate_clinical_interventions
        from trainer import ARTIFACT_PATH, METRICS_PATH, train_and_evaluate_model

class NoShowPredictor:
    _instance: Optional["NoShowPredictor"] = None
    
    def __init__(self):
        self.model = None
        self.metrics = None
        self._load_or_train()
        
    @classmethod
    def get_instance(cls) -> "NoShowPredictor":
        if cls._instance is None:
            cls._instance = NoShowPredictor()
        return cls._instance
        
    def _load_or_train(self):
        if not os.path.exists(ARTIFACT_PATH) or not os.path.exists(METRICS_PATH):
            print("Model artifacts not found. Training model now...")
            self.metrics = train_and_evaluate_model(n_samples=15000)
            self.model = joblib.load(ARTIFACT_PATH)
        else:
            try:
                self.model = joblib.load(ARTIFACT_PATH)
                with open(METRICS_PATH, "r") as f:
                    self.metrics = json.load(f)
            except Exception as e:
                print(f"Error loading artifacts: {e}. Retraining...")
                self.metrics = train_and_evaluate_model(n_samples=15000)
                self.model = joblib.load(ARTIFACT_PATH)
                
    def predict(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw appointment dictionary, runs feature extraction, and returns
        prediction score, risk tier, risk factors, and AI-driven recommendations.
        """
        features_df = extract_features_single(appointment_data)
        probabilities = self.model.predict_proba(features_df)[0]
        risk_score = float(probabilities[1])
        
        # Risk tiering
        if risk_score >= 0.50:
            risk_tier = "HIGH"
        elif risk_score >= 0.25:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"
            
        interventions = generate_clinical_interventions(appointment_data, risk_score)
        
        return {
            "risk_score": round(risk_score, 4),
            "risk_tier": risk_tier,
            "risk_factors": interventions["risk_factors"],
            "ai_headline": interventions["headline"],
            "recommended_actions": interventions["recommended_actions"],
            "revenue_impact_estimate": interventions["revenue_impact_estimate"]
        }
        
    def get_model_metadata(self) -> Dict[str, Any]:
        return self.metrics or {}

# Global accessor
predictor = NoShowPredictor.get_instance()
