"""
MediTrack ML Model Metadata & Retraining Endpoints
"""
from fastapi import APIRouter, Depends, status
from app.ml.predictor import predictor
from app.ml.trainer import train_and_evaluate_model
from app.core.security import get_current_user, require_roles, UserContext, UserRole
from app.core.cache import cache

router = APIRouter()

@router.get("/metrics")
def get_model_metrics(user: UserContext = Depends(get_current_user)):
    """
    Returns current ML model architecture, evaluation metrics, and feature importances.
    """
    return predictor.get_model_metadata()

@router.post("/retrain", status_code=status.HTTP_200_OK)
def trigger_retrain(
    user: UserContext = Depends(require_roles([UserRole.CLINIC_MANAGER]))
):
    """
    Retrains the no-show prediction model on updated historical data.
    RESTRICTED: CLINIC_MANAGER role required.
    """
    new_metrics = train_and_evaluate_model(n_samples=15000)
    predictor._load_or_train()
    cache.invalidate_prefix("appointments:")
    cache.invalidate_prefix("reports:")
    return {
        "message": f"Model successfully retrained by manager {user.username}",
        "metrics": new_metrics
    }
