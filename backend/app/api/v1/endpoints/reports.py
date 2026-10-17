"""
MediTrack Daily Summary & Analytics Report Endpoints
Aggregates daily appointments, computes actual vs predicted no-show rates,
quantifies financial impact, and exports reports. Cached for sub-millisecond retrieval.
"""
from datetime import datetime, date
from typing import Optional
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Appointment
from app.db.schemas import DailySummaryReportResponse
from app.api.v1.endpoints.appointments import serialize_appointment
from app.core.cache import cache
from app.core.security import get_current_user, UserContext

router = APIRouter()

@router.get("/daily-summary", response_model=DailySummaryReportResponse)
def get_daily_summary_report(
    response: Response,
    clinic_id: str = Query("branch-central", description="Clinic ID"),
    date_str: Optional[str] = Query(None, alias="date", description="Report date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """
    Computes comprehensive daily appointment reconciliation summary:
    - Total appointments, completed, actual no-shows, scheduled
    - Actual no-show rate vs AI predicted no-show rate
    - High-risk patient triage list
    - Financial revenue impact analysis
    - Cached with invalidation on appointment updates
    """
    target_date_str = date_str or date.today().isoformat()
    cache_key = f"reports:daily:{clinic_id}:{target_date_str}"
    
    cached_report, is_hit = cache.get(cache_key)
    if is_hit:
        response.headers["X-Cache"] = "HIT"
        response.headers["X-Cache-Key"] = cache_key
        return cached_report
        
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")
        
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    appointments = (
        db.query(Appointment)
        .filter(Appointment.clinic_id == clinic_id)
        .filter(Appointment.scheduled_time >= start_dt, Appointment.scheduled_time <= end_dt)
        .all()
    )
    
    total = len(appointments)
    scheduled = sum(1 for a in appointments if a.status == "SCHEDULED")
    completed = sum(1 for a in appointments if a.status == "COMPLETED")
    no_shows = sum(1 for a in appointments if a.status == "NO_SHOW")
    cancelled = sum(1 for a in appointments if a.status == "CANCELLED")
    
    reconciled_total = completed + no_shows
    actual_rate = (no_shows / reconciled_total * 100.0) if reconciled_total > 0 else 0.0
    
    predicted_expected = sum(a.risk_score for a in appointments)
    predicted_rate = (predicted_expected / total * 100.0) if total > 0 else 0.0
    
    high_risk = sum(1 for a in appointments if a.risk_tier == "HIGH")
    med_risk = sum(1 for a in appointments if a.risk_tier == "MEDIUM")
    low_risk = sum(1 for a in appointments if a.risk_tier == "LOW")
    
    total_rev_at_risk = sum(a.risk_score * (a.revenue_impact_estimate or 120.0) for a in appointments)
    lost_revenue = no_shows * 120.0
    
    # Department breakdown
    dept_map = {}
    for a in appointments:
        dept = a.department
        if dept not in dept_map:
            dept_map[dept] = {"department": dept, "total": 0, "no_shows": 0, "completed": 0, "sum_risk": 0.0}
        dept_map[dept]["total"] += 1
        if a.status == "NO_SHOW":
            dept_map[dept]["no_shows"] += 1
        elif a.status == "COMPLETED":
            dept_map[dept]["completed"] += 1
        dept_map[dept]["sum_risk"] += a.risk_score
        
    department_breakdown = []
    for dept, d in dept_map.items():
        department_breakdown.append({
            "department": dept,
            "total_appointments": d["total"],
            "no_shows": d["no_shows"],
            "completed": d["completed"],
            "predicted_rate": round((d["sum_risk"] / d["total"]) * 100.0, 1) if d["total"] > 0 else 0.0
        })
        
    # Urgent outreach: Scheduled appointments in HIGH risk tier
    urgent_outreach = [
        serialize_appointment(a)
        for a in appointments
        if a.status == "SCHEDULED" and a.risk_tier == "HIGH"
    ]
    
    report_data = {
        "report_date": target_date_str,
        "clinic_id": clinic_id,
        "clinic_name": appointments[0].clinic_name if appointments else "MediTrack Central Hospital",
        "total_appointments": total,
        "scheduled_count": scheduled,
        "completed_count": completed,
        "no_show_count": no_shows,
        "cancelled_count": cancelled,
        "actual_no_show_rate": round(actual_rate, 1),
        "predicted_no_show_rate": round(predicted_rate, 1),
        "predicted_no_shows_expected": round(predicted_expected),
        "high_risk_count": high_risk,
        "medium_risk_count": med_risk,
        "low_risk_count": low_risk,
        "total_revenue_at_risk": round(total_rev_at_risk, 2),
        "revenue_lost_from_no_shows": round(lost_revenue, 2),
        "department_breakdown": department_breakdown,
        "urgent_outreach_list": urgent_outreach
    }
    
    # Cache for 180s
    cache.set(cache_key, report_data, ttl=180)
    
    response.headers["X-Cache"] = "MISS"
    response.headers["X-Cache-Key"] = cache_key
    return report_data

@router.get("/export")
def export_reconciliation_csv(
    clinic_id: str = Query("branch-central"),
    date_str: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user)
):
    """
    Exports daily appointment reconciliation data into a downloadable CSV report.
    """
    target_date_str = date_str or date.today().isoformat()
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")
        
    start_dt = datetime.combine(target_date, datetime.min.time())
    end_dt = datetime.combine(target_date, datetime.max.time())
    
    appointments = (
        db.query(Appointment)
        .filter(Appointment.clinic_id == clinic_id)
        .filter(Appointment.scheduled_time >= start_dt, Appointment.scheduled_time <= end_dt)
        .order_by(Appointment.scheduled_time.asc())
        .all()
    )
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Appointment ID", "Patient Name", "Age", "Phone", "Department",
        "Scheduled Time", "Status", "Risk Score", "Risk Tier",
        "Prior Misses", "SMS Sent", "Reconciled By", "Reconciled At", "Notes"
    ])
    
    for a in appointments:
        writer.writerow([
            a.id, a.patient_name, a.age, a.patient_phone, a.department,
            a.scheduled_time.strftime("%Y-%m-%d %H:%M") if a.scheduled_time else "",
            a.status, f"{a.risk_score:.1%}", a.risk_tier,
            a.prior_no_shows, "Yes" if a.sms_reminder else "No",
            a.reconciled_by or "", a.reconciled_at.strftime("%Y-%m-%d %H:%M") if a.reconciled_at else "",
            a.reconciliation_notes or ""
        ])
        
    output.seek(0)
    filename = f"meditrack_reconciliation_{clinic_id}_{target_date_str}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
