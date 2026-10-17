"""
MediTrack Configuration Settings
"""
from pydantic import BaseModel
import os

class Settings(BaseModel):
    PROJECT_NAME: str = "MediTrack - AI Appointment Reconciliation"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./meditrack.db")
    
    # Caching
    CACHE_DEFAULT_TTL_SECONDS: int = int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "300"))
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    # Clinic Branches
    CLINIC_BRANCHES: list[dict] = [
        {"id": "branch-central", "name": "MediTrack Central Hospital", "city": "Downtown Metro"},
        {"id": "branch-west", "name": "MediTrack Westside Clinic", "city": "West Suburbs"},
        {"id": "branch-north", "name": "MediTrack North Ambulatory", "city": "North District"}
    ]

settings = Settings()
