"""
MediTrack Appointment Management & Reconciliation API Endpoints
Integrates real-time ML inference, caching layer, and audit tracking.
"""
import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Appointment, AuditLog, generate_id
from app.db.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentReconcileRequest,
    AppointmentBatchCreateRequest,
    PredictionRequest,
    PredictionResponse
)
from app.ml.predictor import predictor
from app.core.cache import cache
from app.core.security import get_current_user, require_roles, UserContext, UserRole

router = APIRouter()

def serialize_appointment(apt: Appointment) -> dict:
    """Helper to convert Appointment model to JSON-serializable dictionary."""
    try:
        factors = json.loads(apt.risk_factors_json) if apt.risk_factors_json else []
    except Exception:
        factors = []
        
    try:
        actions = json.loads(apt.recommended_actions_json) if apt.recommended_actions_json else []
    except Exception:
        actions = []
        
    return {
        "id": apt.id,
        "patient_id": apt.patient_id,
        "patient_name": apt.patient_name,
        "patient_phone": apt.patient_phone,
        "age": apt.age,
        "clinic_id": apt.clinic_id,
        "clinic_name": apt.clinic_name,
        "department": apt.department,
        "scheduled_time": apt.scheduled_time.isoformat() if apt.scheduled_time else None,
        "booking_time": apt.booking_time.isoformat() if apt.booking_time else None,
        "lead_days": apt.lead_days,
        "status": apt.status,
        "reconciled_at": apt.reconciled_at.isoformat() if apt.reconciled_at else None,
        "reconciled_by": apt.reconciled_by,
        "reconciliation_notes": apt.reconciliation_notes,
        "sms_reminder": apt.sms_reminder,
        "prior_appointments": apt.prior_appointments,
        "prior_no_shows": apt.prior_no_shows,
        "chronic_condition": apt.chronic_condition,
        "risk_score": apt.risk_score,
        "risk_tier": apt.risk_tier,
        "risk_factors": factors,
        "ai_headline": apt.ai_headline,
        "recommended_actions": actions,
        "revenue_impact_estimate": apt.revenue_impact_estimate,
        "created_at": apt.created_at.isoformat() if apt.created_at else None,
        "updated_at": apt.updated_at.isoformat() if apt.updated_at else None,
    }

@router.get("", response_model=List[AppointmentResponse])
def get_appointments(
    response: Response,
    clinic_id: str = Query("branch-central", description="Filter by clinic ID"),
    date_str: Optional[str] = Query(None, alias="date", description="Filter by scheduled date YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="Filter by status (SCHEDULED, COMPLETED, NO_SHOW, CANCELLED)"),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier (LOW, MEDIUM, HIGH)"),
    search: Optional[str] = Query(None, description="Search by patient name"),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """
    List clinic appointments with optional filters.
    Utilizes caching layer for high performance.
    Sets 'X-Cache' header to 'HIT' or 'MISS'.
    """
    cache_key = f"appointments:list:{clinic_id}:{date_str}:{status}:{risk_tier}:{search}"
    cached_data, is_hit = cache.get(cache_key)
    
    if is_hit:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return cached_data

    # Query DB
    query = db.query(Appointment).filter(Appointment.clinic_id == clinic_id)
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_dt = datetime.combine(target_date, datetime.min.time())
            end_dt = datetime.combine(target_date, datetime.max.time())
            query = query.filter(Appointment.scheduled_time >= start_dt, Appointment.scheduled_time <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")
            
    if status:
        query = query.filter(Appointment.status == status.upper())
        
    if risk_tier:
        query = query.filter(Appointment.risk_tier == risk_tier.upper())
        
    if search:
        query = query.filter(Appointment.patient_name.ilike(f"%{search}%"))
        
    # Order by scheduled time ascending
    appointments = query.order_by(Appointment.scheduled_time.asc()).all()
    serialized = [serialize_appointment(apt) for apt in appointments]
    
    # Store in cache with 120s TTL
    cache.set(cache_key, serialized, ttl=120)
    
    response.headers["X-Cache"] = "MISS"
    response.headers["X-Cache-Key"] = cache_key
    return serialized

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """
    Creates a new appointment.
    Computes lead days and triggers real-time ML inference for no-show risk.
    Invalidates appointment and report cache entries.
    """
    booking_dt = payload.booking_time or datetime.now()
    lead_days = max(0, (payload.scheduled_time.date() - booking_dt.date()).days)
    
    # Feature payload for ML prediction
    ml_input = {
        "age": payload.age,
        "lead_days": lead_days,
        "day_of_week": payload.scheduled_time.weekday(),
        "hour": payload.scheduled_time.hour,
        "prior_appointments": payload.prior_appointments,
        "prior_no_shows": payload.prior_no_shows,
        "sms_reminder": payload.sms_reminder,
        "chronic_condition": payload.chronic_condition,
        "department": payload.department
    }
    
    prediction = predictor.predict(ml_input)
    
    apt = Appointment(
        id=generate_id("apt"),
        patient_id=generate_id("pat"),
        patient_name=payload.patient_name.strip(),
        patient_phone=payload.patient_phone,
        age=payload.age,
        clinic_id=payload.clinic_id,
        clinic_name=payload.clinic_name or "MediTrack Central Hospital",
        department=payload.department,
        scheduled_time=payload.scheduled_time,
        booking_time=booking_dt,
        lead_days=lead_days,
        status=payload.initial_status or "SCHEDULED",
        sms_reminder=payload.sms_reminder,
        prior_appointments=payload.prior_appointments,
        prior_no_shows=payload.prior_no_shows,
        chronic_condition=payload.chronic_condition,
        risk_score=prediction["risk_score"],
        risk_tier=prediction["risk_tier"],
        risk_factors_json=json.dumps(prediction["risk_factors"]),
        ai_headline=prediction["ai_headline"],
        recommended_actions_json=json.dumps(prediction["recommended_actions"]),
        revenue_impact_estimate=prediction["revenue_impact_estimate"]
    )
    
    db.add(apt)
    
    audit = AuditLog(
        appointment_id=apt.id,
        action="CREATED",
        performed_by=user.username,
        role=user.role.value,
        old_status=None,
        new_status=apt.status,
        notes=f"Initial appointment booked with risk tier {apt.risk_tier} ({apt.risk_score:.0%})"
    )
    db.add(audit)
    db.commit()
    db.refresh(apt)
    
    # Invalidate cache
    cache.invalidate_prefix("appointments:")
    cache.invalidate_prefix("reports:")
    
    return serialize_appointment(apt)

@router.patch("/{appointment_id}/reconcile", response_model=AppointmentResponse)
def reconcile_appointment(
    appointment_id: str,
    payload: AppointmentReconcileRequest,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """
    Reconciles an appointment (e.g. mark COMPLETED, NO_SHOW, or CANCELLED).
    Records timestamp, staff identifier, and audit trail.
    Invalidates related cache entries immediately.
    """
    apt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    old_status = apt.status
    apt.status = payload.status
    apt.reconciled_at = datetime.now()
    apt.reconciled_by = user.username
    if payload.notes:
        apt.reconciliation_notes = payload.notes
        
    audit = AuditLog(
        appointment_id=apt.id,
        action="RECONCILED",
        performed_by=user.username,
        role=user.role.value,
        old_status=old_status,
        new_status=apt.status,
        notes=payload.notes or f"Status changed from {old_status} to {apt.status}"
    )
    db.add(audit)
    db.commit()
    db.refresh(apt)
    
    # Invalidate cache
    cache.invalidate_prefix("appointments:")
    cache.invalidate_prefix("reports:")
    
    return serialize_appointment(apt)

@router.post("/predict", response_model=PredictionResponse)
def predict_no_show_endpoint(payload: PredictionRequest):
    """
    Standalone prediction endpoint for ad-hoc evaluations and testing ML feature interactions.
    """
    result = predictor.predict(payload.dict())
    return result

@router.post("/batch-seed", status_code=status.HTTP_201_CREATED)
def seed_demo_appointments(
    clinic_id: str = "branch-central",
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """
    Seeds realistic demonstration appointments for today's schedule,
    featuring a diverse range of risk tiers, departments, and pre-existing statuses.
    """
    now = datetime.now()
    today = now.date()
    
    sample_patients = [
        {"name": "Eleanor Vance", "age": 72, "dept": "Cardiology", "prior_appts": 5, "prior_no_shows": 0, "sms": True, "lead": 4, "hour": 9, "chronic": True, "status": "COMPLETED"},
        {"name": "Marcus Chen", "age": 24, "dept": "General Medicine", "prior_appts": 3, "prior_no_shows": 2, "sms": False, "lead": 18, "hour": 8, "chronic": False, "status": "SCHEDULED"},
        {"name": "Sophia Rodriguez", "age": 31, "dept": "Dermatology", "prior_appts": 1, "prior_no_shows": 1, "sms": False, "lead": 22, "hour": 17, "chronic": False, "status": "SCHEDULED"},
        {"name": "David Kim", "age": 45, "dept": "Orthopedics", "prior_appts": 4, "prior_no_shows": 0, "sms": True, "lead": 6, "hour": 10, "chronic": False, "status": "SCHEDULED"},
        {"name": "Amina Al-Mansoor", "age": 63, "dept": "Endocrinology", "prior_appts": 8, "prior_no_shows": 1, "sms": True, "lead": 12, "hour": 11, "chronic": True, "status": "SCHEDULED"},
        {"name": "Tyler Brooks", "age": 21, "dept": "Pediatrics", "prior_appts": 0, "prior_no_shows": 0, "sms": False, "lead": 15, "hour": 14, "chronic": False, "status": "SCHEDULED"},
        {"name": "Brenda Watson", "age": 58, "dept": "Neurology", "prior_appts": 6, "prior_no_shows": 0, "sms": True, "lead": 8, "hour": 13, "chronic": True, "status": "SCHEDULED"},
        {"name": "James O'Connor", "age": 29, "dept": "General Medicine", "prior_appts": 2, "prior_no_shows": 2, "sms": False, "lead": 28, "hour": 17, "chronic": False, "status": "NO_SHOW"},
        {"name": "Grace Hopper", "age": 82, "dept": "Cardiology", "prior_appts": 10, "prior_no_shows": 0, "sms": True, "lead": 3, "hour": 15, "chronic": True, "status": "SCHEDULED"},
        {"name": "Lucas Morales", "age": 36, "dept": "Orthopedics", "prior_appts": 2, "prior_no_shows": 0, "sms": True, "lead": 5, "hour": 16, "chronic": False, "status": "SCHEDULED"},
        {"name": "Chloe Bennett", "age": 27, "dept": "Dermatology", "prior_appts": 4, "prior_no_shows": 3, "sms": False, "lead": 21, "hour": 8, "chronic": False, "status": "SCHEDULED"},
        {"name": "Arthur Pendelton", "age": 69, "dept": "General Medicine", "prior_appts": 7, "prior_no_shows": 0, "sms": True, "lead": 2, "hour": 10, "chronic": True, "status": "COMPLETED"},
    ]
    
    created_count = 0
    for p in sample_patients:
        scheduled_time = datetime.combine(today, datetime.min.time()) + timedelta(hours=p["hour"])
        booking_time = scheduled_time - timedelta(days=p["lead"])
        
        ml_input = {
            "age": p["age"],
            "lead_days": p["lead"],
            "day_of_week": scheduled_time.weekday(),
            "hour": p["hour"],
            "prior_appointments": p["prior_appts"],
            "prior_no_shows": p["prior_no_shows"],
            "sms_reminder": p["sms"],
            "chronic_condition": p["chronic"],
            "department": p["dept"]
        }
        
        pred = predictor.predict(ml_input)
        
        apt = Appointment(
            id=generate_id("apt"),
            patient_id=generate_id("pat"),
            patient_name=p["name"],
            patient_phone=f"+1 (555) {400 + created_count}-{1000 + created_count * 7}",
            age=p["age"],
            clinic_id=clinic_id,
            clinic_name="MediTrack Central Hospital",
            department=p["dept"],
            scheduled_time=scheduled_time,
            booking_time=booking_time,
            lead_days=p["lead"],
            status=p["status"],
            sms_reminder=p["sms"],
            prior_appointments=p["prior_appts"],
            prior_no_shows=p["prior_no_shows"],
            chronic_condition=p["chronic"],
            risk_score=pred["risk_score"],
            risk_tier=pred["risk_tier"],
            risk_factors_json=json.dumps(pred["risk_factors"]),
            ai_headline=pred["ai_headline"],
            recommended_actions_json=json.dumps(pred["recommended_actions"]),
            revenue_impact_estimate=pred["revenue_impact_estimate"],
            reconciled_at=datetime.now() if p["status"] != "SCHEDULED" else None,
            reconciled_by="Seed Script" if p["status"] != "SCHEDULED" else None
        )
        db.add(apt)
        created_count += 1
        
    db.commit()
    cache.invalidate_prefix("appointments:")
    cache.invalidate_prefix("reports:")
    return {"message": f"Successfully seeded {created_count} demo appointments for {today.isoformat()}"}
