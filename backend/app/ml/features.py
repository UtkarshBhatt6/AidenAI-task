"""
MediTrack Feature Extraction and Transformation Pipeline
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np

CATEGORICAL_COLS = ["department"]
NUMERIC_COLS = [
    "age",
    "lead_days",
    "day_of_week",
    "hour",
    "prior_appointments",
    "prior_no_shows",
    "prior_no_show_ratio",
    "is_first_time",
    "sms_reminder",
    "chronic_condition"
]

ALL_FEATURE_COLS = NUMERIC_COLS + [
    f"dept_{dept.lower().replace(' ', '_')}" 
    for dept in [
        "Cardiology", "Dermatology", "Endocrinology", 
        "General Medicine", "Neurology", "Orthopedics", "Pediatrics"
    ]
]

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes derived domain-specific clinical features:
    - prior_no_show_ratio: proportion of past appointments missed
    - is_first_time: flag for zero appointment history
    - One-hot encoded clinic departments
    """
    df = df.copy()
    
    # Prior no show ratio calculation with safeguard for zero division
    df["prior_appointments"] = df["prior_appointments"].fillna(0).astype(int)
    df["prior_no_shows"] = df["prior_no_shows"].fillna(0).astype(int)
    df["is_first_time"] = (df["prior_appointments"] == 0).astype(int)
    
    df["prior_no_show_ratio"] = np.where(
        df["prior_appointments"] > 0,
        df["prior_no_shows"] / np.maximum(df["prior_appointments"], 1),
        0.18 # Population average prior assumption for first-timers
    )
    
    # Ensure all departments are represented with stable columns
    departments = [
        "Cardiology", "Dermatology", "Endocrinology", 
        "General Medicine", "Neurology", "Orthopedics", "Pediatrics"
    ]
    for dept in departments:
        col_name = f"dept_{dept.lower().replace(' ', '_')}"
        df[col_name] = (df["department"] == dept).astype(int)
        
    return df[ALL_FEATURE_COLS]

def extract_features_single(appointment: Dict[str, Any]) -> pd.DataFrame:
    """
    Prepares a single appointment payload into the exact DataFrame structure
    expected by the trained ML pipeline.
    """
    row = {
        "age": appointment.get("age", 40),
        "lead_days": appointment.get("lead_days", 3),
        "day_of_week": appointment.get("day_of_week", 1),
        "hour": appointment.get("hour", 10),
        "prior_appointments": appointment.get("prior_appointments", 1),
        "prior_no_shows": appointment.get("prior_no_shows", 0),
        "sms_reminder": 1 if appointment.get("sms_reminder", False) else 0,
        "chronic_condition": 1 if appointment.get("chronic_condition", False) else 0,
        "department": appointment.get("department", "General Medicine")
    }
    df = pd.DataFrame([row])
    return engineer_features(df)
