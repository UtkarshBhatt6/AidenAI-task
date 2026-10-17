"""
MediTrack ML Model - Dataset Generation & Feature Engineering
Based on clinical no-show dynamics observed in real-world outpatient datasets
(e.g., lead time, age, prior appointment history, SMS reminders, appointment time).
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

CLINIC_DEPARTMENTS = [
    "General Medicine",
    "Cardiology",
    "Pediatrics",
    "Orthopedics",
    "Dermatology",
    "Endocrinology",
    "Neurology"
]

def generate_synthetic_historical_data(n_samples: int = 12000) -> pd.DataFrame:
    """
    Generates realistic historical outpatient clinic appointment data
    with medically grounded correlations for no-show behavior:
    1. Lead days: longer booking-to-appointment delay -> higher no-show probability
    2. Prior no-shows: past no-show record -> strong repeat predictor
    3. SMS reminders: receiving reminder -> ~30-40% reduction in no-show
    4. Age: young adults (18-30) have higher no-show rate than seniors (60+)
    5. Appointment hour: early mornings & late afternoons have higher no-show
    6. Day of week: Mondays & Fridays have slightly elevated no-show
    7. Chronic conditions: patients with chronic care have slightly better adherence
    """
    data = []
    base_date = datetime(2025, 1, 1)

    for i in range(n_samples):
        # Patient demographics
        age = int(np.clip(np.random.normal(45, 20), 5, 95))
        chronic_condition = 1 if (age > 50 and random.random() < 0.45) else (1 if random.random() < 0.15 else 0)
        
        # Appointment scheduling
        department = random.choice(CLINIC_DEPARTMENTS)
        lead_days = int(np.clip(np.random.exponential(scale=10), 0, 90))
        
        # Date & time
        scheduled_date = base_date + timedelta(days=random.randint(0, 365))
        day_of_week = scheduled_date.weekday() # 0 = Monday, 6 = Sunday (clinics open Mon-Sat: 0-5)
        if day_of_week == 6: # Move Sunday to Monday
            day_of_week = 0
            scheduled_date += timedelta(days=1)
            
        hour = random.choice([8, 9, 10, 11, 13, 14, 15, 16, 17])
        
        # Prior history
        prior_appointments = int(np.clip(np.random.poisson(lam=3), 0, 20))
        if prior_appointments == 0:
            prior_no_shows = 0
        else:
            prior_no_shows = np.random.binomial(n=prior_appointments, p=0.20)
            
        # SMS reminder: more likely sent if lead_days > 2
        sms_reminder = 1 if (lead_days >= 2 and random.random() < 0.72) else (1 if random.random() < 0.30 else 0)
        
        # Calculate latent probability of no-show using logistic sigmoid
        # Base logit: ~ -1.8 (corresponds to ~15-20% baseline clinic no-show rate)
        logit = -1.80
        
        # Lead time impact: longer booking delay strongly correlates with no-shows
        logit += min(lead_days, 45) * 0.048
        
        # Prior no-show history: dominant predictor in outpatient clinics
        if prior_appointments > 0:
            prior_rate = prior_no_shows / prior_appointments
            logit += (prior_rate - 0.20) * 3.2
        else:
            # First-time patient without historical baseline
            logit += 0.35
            
        # SMS reminder benefit: significant adherence booster
        if sms_reminder == 1:
            logit -= 1.15
            
        # Age curve: younger patients (18-28) miss more often, elderly (65+) attend more reliably
        if 18 <= age <= 28:
            logit += 0.55
        elif age >= 65:
            logit -= 0.60
            
        # Chronic condition: regular monitoring needed
        if chronic_condition == 1:
            logit -= 0.40
            
        # Day of week: Monday (+0.20), Friday (+0.25)
        if day_of_week in [0, 4]:
            logit += 0.20
            
        # Hour: 8 AM rush (+0.25) or 5 PM end-of-day (+0.30)
        if hour in [8, 17]:
            logit += 0.25
            
        # Department variation
        dept_risk_adjust = {
            "General Medicine": 0.10,
            "Cardiology": -0.30,
            "Pediatrics": -0.15,
            "Orthopedics": 0.05,
            "Dermatology": 0.25,
            "Endocrinology": -0.20,
            "Neurology": -0.25
        }
        logit += dept_risk_adjust.get(department, 0.0)
        
        # Sigmoid probability
        prob = 1.0 / (1.0 + np.exp(-logit))
        # Actual outcome
        no_show = 1 if random.random() < prob else 0
        
        data.append({
            "age": age,
            "chronic_condition": chronic_condition,
            "department": department,
            "lead_days": lead_days,
            "day_of_week": day_of_week,
            "hour": hour,
            "prior_appointments": prior_appointments,
            "prior_no_shows": prior_no_shows,
            "sms_reminder": sms_reminder,
            "no_show": no_show
        })
        
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    df = generate_synthetic_historical_data(12000)
    print(f"Generated {len(df)} historical appointment records.")
    print(f"Overall No-show rate: {df['no_show'].mean():.2%}")
    print(df.head())
