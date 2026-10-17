"""
MediTrack API Integration, Caching, and RBAC Test Suite
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.cache import cache
from app.db.database import Base, engine, SessionLocal
from app.db.models import Appointment, AuditLog

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup

@pytest.fixture
def client():
    # Clear cache before each test
    cache.clear()
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_appointment_and_prediction(client):
    """
    MUST Requirement: Staff inputs appointment data -> stored correctly.
    MUST Requirement: Model predicts likelihood of no-show -> returns prediction.
    """
    tomorrow = datetime.now() + timedelta(days=2)
    payload = {
        "patient_name": "Alexander Hayes",
        "patient_phone": "+1 (555) 789-0123",
        "age": 45,
        "clinic_id": "branch-central",
        "department": "Cardiology",
        "scheduled_time": tomorrow.isoformat(),
        "sms_reminder": True,
        "prior_appointments": 3,
        "prior_no_shows": 0,
        "chronic_condition": True
    }
    
    headers = {"X-User-Role": "CLINIC_STAFF", "X-User-Name": "Nurse Sarah"}
    response = client.post("/api/v1/appointments", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    
    assert data["patient_name"] == "Alexander Hayes"
    assert data["status"] == "SCHEDULED"
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_tier"] in ["LOW", "MEDIUM", "HIGH"]
    assert len(data["risk_factors"]) > 0
    assert "ai_headline" in data

def test_reconcile_appointment_status(client):
    """
    MUST Requirement: Reconcile daily appointment no-show status.
    """
    # Create appointment
    tomorrow = datetime.now() + timedelta(days=1)
    create_res = client.post("/api/v1/appointments", json={
        "patient_name": "Test Reconcile Patient",
        "age": 30,
        "clinic_id": "branch-central",
        "department": "General Medicine",
        "scheduled_time": tomorrow.isoformat()
    })
    apt_id = create_res.json()["id"]
    
    # Reconcile as NO_SHOW
    reconcile_res = client.patch(
        f"/api/v1/appointments/{apt_id}/reconcile",
        json={"status": "NO_SHOW", "notes": "Patient did not answer phone calls"},
        headers={"X-User-Role": "CLINIC_STAFF", "X-User-Name": "Receptionist John"}
    )
    assert reconcile_res.status_code == 200
    updated = reconcile_res.json()
    assert updated["status"] == "NO_SHOW"
    assert updated["reconciled_by"] == "Receptionist John"
    assert updated["reconciliation_notes"] == "Patient did not answer phone calls"
    assert updated["reconciled_at"] is not None

def test_caching_layer_hits_misses_and_invalidation(client):
    """
    SHOULD Requirement: Caching layer stores frequently accessed appointment data.
    Check: First request = MISS, second request = HIT.
    Mutation (new appointment or reconciliation) invalidates cache -> Next request = MISS.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    url = f"/api/v1/appointments?clinic_id=branch-central&date={today_str}"
    
    # First request: Cache MISS
    res1 = client.get(url)
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"
    
    # Second request: Cache HIT
    res2 = client.get(url)
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"
    assert len(res1.json()) == len(res2.json())
    
    # Invalidation trigger: Create a new appointment
    client.post("/api/v1/appointments", json={
        "patient_name": "Cache Invalidation Probe",
        "age": 29,
        "clinic_id": "branch-central",
        "department": "Pediatrics",
        "scheduled_time": (datetime.now() + timedelta(hours=1)).isoformat()
    })
    
    # Third request: Should be Cache MISS because cache was invalidated by the mutation
    res3 = client.get(url)
    assert res3.status_code == 200
    assert res3.headers.get("X-Cache") == "MISS"

def test_daily_summary_report(client):
    """
    SHOULD Requirement: Summary report of daily appointments,
    including number of no-shows and predicted no-show rates.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    url = f"/api/v1/reports/daily-summary?clinic_id=branch-central&date={today_str}"
    
    # Call report
    res = client.get(url)
    assert res.status_code == 200
    report = res.json()
    
    assert "total_appointments" in report
    assert "no_show_count" in report
    assert "actual_no_show_rate" in report
    assert "predicted_no_show_rate" in report
    assert "total_revenue_at_risk" in report
    assert "department_breakdown" in report
    assert isinstance(report["department_breakdown"], list)
    
    # Verify report caching
    res_cached = client.get(url)
    assert res_cached.headers.get("X-Cache") == "HIT"

def test_rbac_access_control(client):
    """
    COULD Requirement: Role-based access control restricts functionalities.
    CLINIC_STAFF is denied access (403) for manager-only routes (clear cache, audit logs).
    CLINIC_MANAGER is granted access (200).
    """
    # Staff tries to clear cache -> 403 Forbidden
    staff_res = client.post("/api/v1/cache/clear", headers={"X-User-Role": "CLINIC_STAFF"})
    assert staff_res.status_code == 403
    assert "Access denied" in staff_res.json()["detail"]
    
    # Staff tries to view audit logs -> 403 Forbidden
    staff_audit = client.get("/api/v1/audit/logs", headers={"X-User-Role": "CLINIC_STAFF"})
    assert staff_audit.status_code == 403
    
    # Manager clears cache -> 200 OK
    manager_res = client.post("/api/v1/cache/clear", headers={"X-User-Role": "CLINIC_MANAGER"})
    assert manager_res.status_code == 200
    assert manager_res.json()["status"] == "success"
    
    # Manager views audit logs -> 200 OK
    manager_audit = client.get("/api/v1/audit/logs", headers={"X-User-Role": "CLINIC_MANAGER"})
    assert manager_audit.status_code == 200
    assert isinstance(manager_audit.json(), list)
