"""
MediTrack SQLAlchemy Database Models
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import Base

def generate_id(prefix: str = "apt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def utc_now():
    return datetime.now(timezone.utc)

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(String(32), primary_key=True, default=lambda: generate_id("apt"), index=True)
    patient_id = Column(String(32), index=True)
    patient_name = Column(String(128), nullable=False, index=True)
    patient_phone = Column(String(32), nullable=True)
    age = Column(Integer, default=35)
    
    clinic_id = Column(String(64), nullable=False, index=True, default="branch-central")
    clinic_name = Column(String(128), default="MediTrack Central Hospital")
    department = Column(String(64), nullable=False, default="General Medicine", index=True)
    
    scheduled_time = Column(DateTime, nullable=False, index=True)
    booking_time = Column(DateTime, default=utc_now)
    lead_days = Column(Integer, default=0)
    
    # Status: SCHEDULED, COMPLETED, NO_SHOW, CANCELLED
    status = Column(String(32), nullable=False, default="SCHEDULED", index=True)
    
    # Reconciliation metadata
    reconciled_at = Column(DateTime, nullable=True)
    reconciled_by = Column(String(128), nullable=True)
    reconciliation_notes = Column(Text, nullable=True)
    
    # Clinical predictors
    sms_reminder = Column(Boolean, default=False)
    prior_appointments = Column(Integer, default=0)
    prior_no_shows = Column(Integer, default=0)
    chronic_condition = Column(Boolean, default=False)
    
    # AI / ML predictions
    risk_score = Column(Float, default=0.0)
    risk_tier = Column(String(16), default="LOW", index=True) # LOW, MEDIUM, HIGH
    risk_factors_json = Column(Text, default="[]") # JSON encoded list
    ai_headline = Column(String(255), nullable=True)
    recommended_actions_json = Column(Text, default="[]") # JSON encoded list
    revenue_impact_estimate = Column(Float, default=120.0)
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Composite indexes for daily query acceleration
    __table_args__ = (
        Index("idx_clinic_scheduled_date", "clinic_id", "scheduled_time"),
        Index("idx_clinic_status", "clinic_id", "status"),
        Index("idx_clinic_risk_tier", "clinic_id", "risk_tier"),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(32), primary_key=True, default=lambda: generate_id("aud"))
    appointment_id = Column(String(32), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(64), nullable=False) # e.g. CREATED, RECONCILED, STATUS_OVERRIDE
    performed_by = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
