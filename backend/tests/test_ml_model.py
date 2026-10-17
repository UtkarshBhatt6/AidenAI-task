"""
MediTrack ML Model Tests
Verifies feature engineering, model inference, prediction bounds, and edge cases.
"""
import pytest
from app.ml.features import extract_features_single, ALL_FEATURE_COLS
from app.ml.predictor import predictor
from app.ml.insights import generate_clinical_interventions

def test_feature_extraction_completeness():
    sample = {
        "age": 42,
        "lead_days": 10,
        "day_of_week": 2,
        "hour": 14,
        "prior_appointments": 4,
        "prior_no_shows": 1,
        "sms_reminder": True,
        "chronic_condition": False,
        "department": "Cardiology"
    }
    df = extract_features_single(sample)
    assert df.shape[0] == 1
    assert set(df.columns) == set(ALL_FEATURE_COLS)
    assert df["dept_cardiology"].values[0] == 1
    assert df["dept_pediatrics"].values[0] == 0
    assert df["prior_no_show_ratio"].values[0] == 0.25

def test_prediction_output_structure():
    sample = {
        "age": 25,
        "lead_days": 21,
        "day_of_week": 0, # Monday
        "hour": 8, # Early morning rush
        "prior_appointments": 2,
        "prior_no_shows": 2, # High past no-show rate
        "sms_reminder": False, # No reminder
        "chronic_condition": False,
        "department": "Dermatology"
    }
    result = predictor.predict(sample)
    assert "risk_score" in result
    assert 0.0 <= result["risk_score"] <= 1.0
    assert result["risk_tier"] in ["LOW", "MEDIUM", "HIGH"]
    assert len(result["risk_factors"]) > 0
    assert len(result["recommended_actions"]) > 0
    assert result["revenue_impact_estimate"] > 0
    # High risk expected for 100% past no-show, long lead time, and no SMS
    assert result["risk_tier"] in ["MEDIUM", "HIGH"]

def test_prediction_edge_cases():
    # Extreme age 0 (infant)
    infant = {
        "age": 0,
        "lead_days": 0,
        "day_of_week": 3,
        "hour": 10,
        "prior_appointments": 0,
        "prior_no_shows": 0,
        "sms_reminder": True,
        "chronic_condition": False,
        "department": "Pediatrics"
    }
    res_infant = predictor.predict(infant)
    assert 0.0 <= res_infant["risk_score"] <= 1.0
    
    # Senior citizen with chronic condition and perfect adherence
    senior = {
        "age": 85,
        "lead_days": 2,
        "day_of_week": 2,
        "hour": 11,
        "prior_appointments": 12,
        "prior_no_shows": 0,
        "sms_reminder": True,
        "chronic_condition": True,
        "department": "Cardiology"
    }
    res_senior = predictor.predict(senior)
    assert res_senior["risk_score"] < 0.35 # Low risk expected
    assert res_senior["risk_tier"] == "LOW"

def test_model_metadata_availability():
    meta = predictor.get_model_metadata()
    assert "roc_auc" in meta
    assert meta["roc_auc"] > 0.70
    assert "feature_importances" in meta
