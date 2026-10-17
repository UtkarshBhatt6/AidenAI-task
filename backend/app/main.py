"""
MediTrack Main Application
FastAPI application entrypoint with middleware, database initialization,
and automated seed data loading.
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.database import engine, Base, SessionLocal
from app.api.v1.endpoints import appointments, reports, cache_admin, model_meta, audit
from app.db.models import Appointment

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed demo data if DB is empty
    db = SessionLocal()
    try:
        count = db.query(Appointment).count()
        if count == 0:
            print("Database empty: Auto-seeding initial demo appointments...")
            from app.core.security import UserContext, UserRole
            dummy_user = UserContext(username="System Startup", role=UserRole.CLINIC_MANAGER)
            appointments.seed_demo_appointments(clinic_id="branch-central", db=db, user=dummy_user)
            print("Auto-seeding complete.")
    finally:
        db.close()
        
    yield
    # Cleanup on shutdown if needed

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade AI-powered appointment no-show reconciliation system with caching and RBAC.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache", "X-Cache-Key", "X-Response-Time-ms"]
)

# Latency and telemetry middleware
@app.middleware("http")
async def add_process_time_and_telemetry(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time-ms"] = f"{process_time:.2f}"
    return response

# Register Routers
app.include_router(appointments.router, prefix=f"{settings.API_V1_STR}/appointments", tags=["Appointments"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Reports"])
app.include_router(cache_admin.router, prefix=f"{settings.API_V1_STR}/cache", tags=["Cache Admin"])
app.include_router(model_meta.router, prefix=f"{settings.API_V1_STR}/model", tags=["ML Model"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Audit Trail"])

@app.get("/health", tags=["Health"])
def healthcheck():
    return {
        "status": "healthy",
        "service": "MediTrack Backend API",
        "version": settings.VERSION
    }
