"""
MediTrack Audit Trail Endpoints
RBAC Protected: Restricted to CLINIC_MANAGER role.
"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AuditLog
from app.db.schemas import AuditLogResponse
from app.core.security import require_roles, UserContext, UserRole

router = APIRouter()

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: UserContext = Depends(require_roles([UserRole.CLINIC_MANAGER]))
):
    """
    Returns historical audit trail of all staff reconciliation actions.
    RESTRICTED: CLINIC_MANAGER role required.
    """
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return logs
