"""
MediTrack Pydantic Schemas for Validation and API Serialization
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

class AppointmentBase(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=128)
    patient_phone: Optional[str] = Field(default="+1 (555) 234-5678")
    age: int = Field(default=38, ge=0, le=120)
    
    clinic_id: str = Field(default="branch-central")
    clinic_name: Optional[str] = Field(default="MediTrack Central Hospital")
    department: str = Field(default="General Medicine")
    
    scheduled_time: datetime
    booking_time: Optional[datetime] = Field(default_factory=datetime.now)
    
    sms_reminder: bool = Field(default=True)
    prior_appointments: int = Field(default=2, ge=0)
    prior_no_shows: int = Field(default=0, ge=0)
    chronic_condition: bool = Field(default=False)

    @field_validator("prior_no_shows")
    @classmethod
    def validate_no_shows_not_exceed_appointments(cls, v, values):
        prior_appts = values.data.get("prior_appointments", 0)
        if v > prior_appts:
            pass
        return v

class AppointmentCreate(AppointmentBase):
    initial_status: Optional[str] = Field(default="SCHEDULED", pattern="^(SCHEDULED|COMPLETED|NO_SHOW|CANCELLED)$")

class AppointmentBatchItem(AppointmentBase):
    status: Optional[str] = "SCHEDULED"

class AppointmentBatchCreateRequest(BaseModel):
    appointments: List[AppointmentBatchItem]

class AppointmentReconcileRequest(BaseModel):
    status: str = Field(..., pattern="^(COMPLETED|NO_SHOW|CANCELLED)$")
    notes: Optional[str] = Field(default=None, max_length=500)

class PredictionRequest(BaseModel):
    age: int = Field(default=40, ge=0, le=120)
    lead_days: int = Field(default=5, ge=0)
    day_of_week: int = Field(default=1, ge=0, le=6)
    hour: int = Field(default=10, ge=7, le=20)
    prior_appointments: int = Field(default=2, ge=0)
    prior_no_shows: int = Field(default=0, ge=0)
    sms_reminder: bool = Field(default=True)
    chronic_condition: bool = Field(default=False)
    department: str = Field(default="General Medicine")

class PredictionResponse(BaseModel):
    risk_score: float
    risk_tier: str
    risk_factors: List[str]
    ai_headline: str
    recommended_actions: List[str]
    revenue_impact_estimate: float

class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: Optional[str] = None
    patient_name: str
    patient_phone: Optional[str] = None
    age: int
    clinic_id: str
    clinic_name: str
    department: str
    scheduled_time: datetime
    booking_time: datetime
    lead_days: int
    status: str
    reconciled_at: Optional[datetime] = None
    reconciled_by: Optional[str] = None
    reconciliation_notes: Optional[str] = None
    sms_reminder: bool
    prior_appointments: int
    prior_no_shows: int
    chronic_condition: bool
    risk_score: float
    risk_tier: str
    risk_factors: List[str]
    ai_headline: Optional[str] = None
    recommended_actions: List[str]
    revenue_impact_estimate: float
    created_at: datetime
    updated_at: datetime

class DailySummaryReportResponse(BaseModel):
    report_date: str
    clinic_id: str
    clinic_name: str
    total_appointments: int
    scheduled_count: int
    completed_count: int
    no_show_count: int
    cancelled_count: int
    actual_no_show_rate: float
    predicted_no_show_rate: float
    predicted_no_shows_expected: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    total_revenue_at_risk: float
    revenue_lost_from_no_shows: float
    department_breakdown: List[Dict[str, Any]]
    urgent_outreach_list: List[AppointmentResponse]

class CacheStatsResponse(BaseModel):
    hits: int
    misses: int
    total_requests: int
    hit_ratio_percent: float
    active_keys_count: int
    total_evictions: int
    capacity_evictions: Optional[int] = 0
    ttl_expirations: Optional[int] = 0
    estimated_latency_saved_ms: float
    cache_store_size: int
    max_size: int
    default_ttl_seconds: int
    backend: Optional[str] = "redis"

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    action: str
    performed_by: str
    role: str
    old_status: Optional[str] = None
    new_status: str
    notes: Optional[str] = None
    timestamp: datetime
