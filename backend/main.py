from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from models import Base, engine, SessionLocal
from models.models import TierLimit
from routes import policy, ingest, api, billing, admin, monitoring, templates, tokens
from lib.services.health import check_all_services
from lib.startup_validation import run_validation

app = FastAPI(title="logging.email API", version="1.0.0")

@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    run_validation()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(TierLimit).first():
            db.add(TierLimit(tier='free', max_addresses=3, retention_days=7, rate_limit_per_hour=100, max_storage_mb=100, api_enabled=False, webhook_enabled=False, priority_support=False))
            db.add(TierLimit(tier='paid', max_addresses=50, retention_days=90, rate_limit_per_hour=1000, max_storage_mb=5000, api_enabled=True, webhook_enabled=True, priority_support=True))
            db.commit()
        
        # Create default email templates
        from lib.services.templates import create_default_templates
        create_default_templates(db)
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(policy.router, tags=["Policy"])
app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(api.router, tags=["API"])
app.include_router(billing.router, tags=["Billing"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(monitoring.router, tags=["Monitoring"])
app.include_router(templates.router, tags=["Templates"])
app.include_router(tokens.router, tags=["Tokens"])

@app.get("/health")
def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@app.get("/health/detailed")
def detailed_health_check():
    """Detailed health check with service status"""
    return check_all_services()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
