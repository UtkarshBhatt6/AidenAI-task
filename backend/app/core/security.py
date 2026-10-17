"""
MediTrack Security & Role-Based Access Control (RBAC)
Supports roles: CLINIC_STAFF and CLINIC_MANAGER
Integrates seamlessly via FastAPI Dependencies.
"""
from enum import Enum
from typing import List, Optional
from fastapi import Header, HTTPException, status, Depends

from pydantic import BaseModel

class UserRole(str, Enum):
    CLINIC_STAFF = "CLINIC_STAFF"
    CLINIC_MANAGER = "CLINIC_MANAGER"

class UserContext(BaseModel):
    username: str = "Nurse Sarah Jenkins"
    role: UserRole = UserRole.CLINIC_STAFF
    clinic_id: str = "branch-central"

def get_current_user(
    x_user_role: Optional[str] = Header(default="CLINIC_STAFF", alias="X-User-Role"),
    x_user_name: Optional[str] = Header(default="Nurse Sarah Jenkins", alias="X-User-Name"),
    x_clinic_id: Optional[str] = Header(default="branch-central", alias="X-Clinic-ID")
) -> UserContext:
    """
    Extracts the authenticated user context from request headers.
    Enables quick role-switching in the UI/Demo without burdensome auth overhead,
    while maintaining strict RBAC policy enforcement at the endpoint level.
    """
    role_str = (x_user_role or "CLINIC_STAFF").upper()
    try:
        role = UserRole(role_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user role: {x_user_role}. Must be one of {[r.value for r in UserRole]}"
        )
    return UserContext(username=x_user_name, role=role, clinic_id=x_clinic_id)

def require_roles(allowed_roles: List[UserRole]):
    """
    FastAPI dependency factory enforcing that the authenticated user possesses
    at least one of the specified roles.
    """
    def role_checker(user: UserContext = Depends(get_current_user)) -> UserContext:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Action restricted to: {[r.value for r in allowed_roles]}. Current role: {user.role.value}"
            )
        return user
    return role_checker
