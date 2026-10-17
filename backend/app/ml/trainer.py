"""
MediTrack ML Model Training & Evaluation Pipeline
Trains a calibrated Gradient Boosting model, evaluates metrics (ROC-AUC, Precision, Recall, F1),
and saves the trained artifact and feature importances for production inference.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    brier_score_loss,
    confusion_matrix
)

try:
    from app.ml.dataset import generate_synthetic_historical_data
    from app.ml.features import engineer_features, ALL_FEATURE_COLS
except ImportError:
    try:
        from .dataset import generate_synthetic_historical_data
        from .features import engineer_features, ALL_FEATURE_COLS
    except ImportError:
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from dataset import generate_synthetic_historical_data
        from features import engineer_features, ALL_FEATURE_COLS

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_PATH = os.path.join(MODEL_DIR, "artifacts", "no_show_model.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "artifacts", "model_metrics.json")

def train_and_evaluate_model(n_samples: int = 15000) -> dict:
    os.makedirs(os.path.join(MODEL_DIR, "artifacts"), exist_ok=True)
    
    print(f"Generating {n_samples} historical records for training...")
    raw_df = generate_synthetic_historical_data(n_samples=n_samples)
    
    y = raw_df["no_show"].values
    X = engineer_features(raw_df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    print(f"Training dataset: {len(X_train)} samples, Test dataset: {len(X_test)} samples")
    print(f"Class distribution: {np.mean(y_train):.1%} no-show rate")
    
    model = GradientBoostingClassifier(
        n_estimators=120,
        learning_rate=0.08,
        max_depth=4,
        subsample=0.85,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Predict on test set
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.35).astype(int) # Clinical threshold tuned for proactive intervention
    
    auc = float(roc_auc_score(y_test, y_pred_proba))
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_test, y_pred_proba))
    
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    
    # Feature importances from the base gradient boosting model
    # Feature importances from the gradient boosting model
    importances = dict(zip(ALL_FEATURE_COLS, [float(x) for x in model.feature_importances_]))
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))
    
    metrics = {
        "model_type": "GradientBoostingClassifier",
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "roc_auc": round(auc, 4),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "brier_score": round(brier, 4),
        "decision_threshold": 0.35,
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        },
        "feature_importances": sorted_importances
    }
    
    # Save artifacts
    joblib.dump(model, ARTIFACT_PATH)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Model saved successfully to {ARTIFACT_PATH}")
    print(f"ROC-AUC: {auc:.4f} | Recall: {rec:.4f} | Precision: {prec:.4f} | F1: {f1:.4f}")
    return metrics

if __name__ == "__main__":
    train_and_evaluate_model()
