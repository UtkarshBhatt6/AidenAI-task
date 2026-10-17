"""
MediTrack ML Model Architecture Benchmarking Script
Trains and evaluates candidate architectures (Logistic Regression, Multi-Layer Perceptron, Gradient Boosting)
on the exact same stratified holdout split, measuring empirical ROC-AUC, training duration, and micro-latency.
"""
import os
import json
import time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss

from app.ml.dataset import generate_synthetic_historical_data
from app.ml.features import engineer_features

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
BENCHMARK_FILE = os.path.join(ARTIFACT_DIR, "benchmark_results.json")

def run_benchmarks(n_samples: int = 15000):
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    print(f"Generating {n_samples} samples for comparative architectural benchmarking...")
    raw_df = generate_synthetic_historical_data(n_samples=n_samples)
    y = raw_df["no_show"].values
    X = engineer_features(raw_df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    candidate_models = {
        "Calibrated Gradient Boosting": {
            "model": GradientBoostingClassifier(n_estimators=120, learning_rate=0.08, max_depth=4, subsample=0.85, random_state=42),
            "interpretability": "High (Mean Decrease in Impurity / Feature Importances)",
            "complexity": "Low (Standard Scikit-Learn / Joblib)"
        },
        "Deep Neural Net (MLP)": {
            "model": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300, random_state=42),
            "interpretability": "Low (Black-Box Weights)",
            "complexity": "Medium (Iterative backpropagation, scaling sensitivity)"
        },
        "Logistic Regression": {
            "model": LogisticRegression(max_iter=1000, random_state=42),
            "interpretability": "Very High (Linear Odds Coefficients)",
            "complexity": "Very Low (Convex Optimization)"
        }
    }

    results = []
    print("\nEvaluating candidate architectures on holdout test set (3,000 samples):")
    print("-" * 80)

    for name, config in candidate_models.items():
        m = config["model"]
        
        # Fit timing
        t0 = time.perf_counter()
        m.fit(X_train, y_train)
        fit_time_sec = time.perf_counter() - t0

        # Predict holdout probabilities
        probs = m.predict_proba(X_test)[:, 1]
        auc = float(roc_auc_score(y_test, probs))
        brier = float(brier_score_loss(y_test, probs))

        # Measure single-sample inference latency across 500 iterations
        single_sample = X_test.iloc[[0]]
        latencies = []
        for _ in range(500):
            t_inf = time.perf_counter()
            _ = m.predict_proba(single_sample)
            latencies.append((time.perf_counter() - t_inf) * 1000.0) # in ms

        avg_latency_ms = float(np.mean(latencies))

        record = {
            "model_architecture": name,
            "roc_auc": round(auc, 4),
            "brier_score": round(brier, 4),
            "avg_inference_latency_ms": round(avg_latency_ms, 3),
            "fit_time_sec": round(fit_time_sec, 2),
            "interpretability": config["interpretability"],
            "deployment_complexity": config["complexity"]
        }
        results.append(record)
        print(f"{name:30s} | ROC-AUC: {auc:.4f} | Brier: {brier:.4f} | Latency: {avg_latency_ms:.2f} ms | Fit: {fit_time_sec:.2f}s")

    with open(BENCHMARK_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nBenchmark results saved to {BENCHMARK_FILE}")
    return results

if __name__ == "__main__":
    run_benchmarks()
