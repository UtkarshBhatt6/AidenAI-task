"""
MediTrack Cache Administration & Performance Metrics Endpoints
RBAC Protected: Clear cache is restricted to CLINIC_MANAGER role.
"""
from fastapi import APIRouter, Depends, status
from app.core.cache import cache
from app.db.schemas import CacheStatsResponse
from app.core.security import get_current_user, require_roles, UserContext, UserRole

router = APIRouter()

@router.get("/stats", response_model=CacheStatsResponse)
def get_cache_statistics(user: UserContext = Depends(get_current_user)):
    """
    Returns live performance telemetry of the caching layer:
    total hits, misses, hit ratio %, active entries, and latency saved.
    """
    stats = cache.get_stats()
    return stats

@router.post("/clear", status_code=status.HTTP_200_OK)
def clear_cache(
    user: UserContext = Depends(require_roles([UserRole.CLINIC_MANAGER]))
):
    """
    Flushes all cached entries.
    RESTRICTED: CLINIC_MANAGER role required.
    Staff role attempts will receive HTTP 403 Forbidden.
    """
    cache.clear()
    return {
        "status": "success",
        "message": f"Cache successfully flushed by manager {user.username}.",
        "new_stats": cache.get_stats()
    }
