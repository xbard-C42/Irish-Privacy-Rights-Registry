from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import create_engine, Column, String, JSON, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
import logging
from loguru import logger
import sys

# Configuration
class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./privacy_registry.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    MIN_PASSWORD_LENGTH: int = int(os.getenv("MIN_PASSWORD_LENGTH", "12"))
    TOKEN_EXPIRY_DAYS: int = int(os.getenv("TOKEN_EXPIRY_DAYS", "365"))
    RATE_LIMIT_REQUESTS: str = os.getenv("RATE_LIMIT_REQUESTS", "100/hour")
    
settings = Settings()

# Logging setup
logger.remove()
logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO")
logger.add("privacy_registry.log", rotation="1 day", retention="30 days", level="DEBUG")

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI app
app = FastAPI(
    title="Privacy Rights Registry API",
    description="Production-ready registry for privacy rights with anti-doxxing protection",
    version="1.0.0",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc"
)

# Middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    token = Column(String, unique=True, index=True)
    rights = Column(JSON)
    verified = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    api_key = Column(String, unique=True, index=True)
    contact_email = Column(String)
    is_verified = Column(Boolean, default=False)
    rate_limit_tier = Column(String, default="standard")  # standard, premium, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, index=True)
    company_id = Column(String, index=True)
    user_token = Column(String, index=True)
    action = Column(String, index=True)  # lookup, lookup_blocked_doxxing, violation_reported
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    metadata = Column(JSON)

Base.metadata.create_all(bind=engine)

# Pydantic models with validation
class RightsDeclaration(BaseModel):
    erasure: bool = False
    no_sale: bool = False
    no_profiling: bool = False
    no_marketing: bool = False
    data_portability: bool = False
    access_request: bool = False
    anti_doxxing: bool = False

class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    rights: RightsDeclaration
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < settings.MIN_PASSWORD_LENGTH:
            raise ValueError(f'Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long')
        
        # Check for common patterns
        if v.lower() in ['password', '123456', 'admin', 'letmein']:
            raise ValueError('Password is too common')
        
        # Require mixed case, numbers, symbols
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letters')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letters')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain numbers')
        if not any(c in '!@#$%^&*()' for c in v):
            raise ValueError('Password must contain special characters')
            
        return v

class CompanyRegistration(BaseModel):
    name: str
    contact_email: EmailStr
    
    @validator('name')
    def validate_name(cls, v):
        if len(v) < 2:
            raise ValueError('Company name must be at least 2 characters')
        return v

class AuditLogEntry(BaseModel):
    user_token: str
    action: str
    metadata: Optional[Dict[str, Any]] = None

class ViolationReport(BaseModel):
    user_token: str
    company_name: str
    violation_type: str
    description: str
    evidence_url: Optional[str] = None

# Helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_user_token(user_id: str, rights: dict) -> str:
    """Create a cryptographically signed token for user privacy rights"""
    payload = {
        "user_id": user_id,
        "rights": rights,
        "iat": datetime.utcnow().timestamp(),
        "exp": (datetime.utcnow() + timedelta(days=settings.TOKEN_EXPIRY_DAYS)).timestamp()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_user_token(token: str) -> dict:
    """Verify and decode a user privacy rights token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired token attempted: {token[:20]}...")
        raise HTTPException(status_code=400, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.warning(f"Invalid token attempted: {token[:20]}...")
        raise HTTPException(status_code=400, detail="Invalid token")

def verify_company_api_key(credentials: HTTPAuthorizationCredentials, db: Session):
    """Verify company API key"""
    company = db.query(Company).filter(Company.api_key == credentials.credentials).first()
    if not company:
        logger.warning(f"Invalid API key attempted: {credentials.credentials[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    return company

def get_client_info(request: Request) -> dict:
    """Extract client information for audit logging"""
    return {
        "ip_address": get_remote_address(request),
        "user_agent": request.headers.get("user-agent", ""),
        "timestamp": datetime.utcnow().isoformat()
    }

# API Routes
@app.post("/v1/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_user(request: Request, registration: UserRegistration, db: Session = Depends(get_db)):
    """Register a new user and generate their privacy rights token"""
    
    # Check if user already exists
    if db.query(User).filter(User.email == registration.email).first():
        logger.warning(f"Duplicate registration attempt: {registration.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = secrets.token_urlsafe(16)
    hashed_password = pwd_context.hash(registration.password)
    token = create_user_token(user_id, registration.rights.dict())
    
    user = User(
        id=user_id,
        email=registration.email,
        hashed_password=hashed_password,
        token=token,
        rights=registration.rights.dict()
    )
    
    db.add(user)
    db.commit()
    
    logger.info(f"User registered successfully: {registration.email}")
    
    return {
        "message": "User registered successfully",
        "token": token,
        "rights": registration.rights.dict(),
        "expires_at": (datetime.utcnow() + timedelta(days=settings.TOKEN_EXPIRY_DAYS)).isoformat()
    }

@app.get("/v1/registry/{token}")
@limiter.limit(settings.RATE_LIMIT_REQUESTS)
async def lookup_user_rights(request: Request, token: str, 
                           credentials: HTTPAuthorizationCredentials = Depends(security),
                           db: Session = Depends(get_db)):
    """Company endpoint to look up user privacy rights"""
    
    # Verify company API key
    company = verify_company_api_key(credentials, db)
    
    # Verify user token
    payload = verify_user_token(token)
    rights = payload["rights"]
    
    # Get client info for audit
    client_info = get_client_info(request)
    
    # ENFORCE anti-doxxing protection
    if rights.get("anti_doxxing", False):
        # Log the blocked attempt
        audit_entry = AuditLog(
            id=secrets.token_urlsafe(16),
            company_id=company.id,
            user_token=token,
            action="lookup_blocked_doxxing",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            metadata={
                "company_name": company.name,
                "reason": "User has anti-doxxing protection enabled",
                "blocked_at": client_info["timestamp"]
            }
        )
        db.add(audit_entry)
        db.commit()
        
        logger.warning(f"Anti-doxxing lookup blocked: {company.name} -> {token[:20]}...")
        
        raise HTTPException(
            status_code=403,
            detail="Access denied: User has anti-doxxing protection enabled. Data lookup blocked to prevent stalking/harassment."
        )
    
    # Log the successful lookup
    audit_entry = AuditLog(
        id=secrets.token_urlsafe(16),
        company_id=company.id,
        user_token=token,
        action="lookup_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        metadata={
            "company_name": company.name,
            "rights_returned": rights
        }
    )
    db.add(audit_entry)
    db.commit()
    
    logger.info(f"Rights lookup successful: {company.name} -> {token[:20]}...")
    
    return {
        "rights": rights,
        "token_valid": True,
        "lookup_timestamp": datetime.utcnow().isoformat(),
        "company_id": company.id
    }

@app.post("/v1/company/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_company(request: Request, registration: CompanyRegistration, db: Session = Depends(get_db)):
    """Register a company and generate API key"""
    
    # Check if company already exists
    if db.query(Company).filter(Company.contact_email == registration.contact_email).first():
        logger.warning(f"Duplicate company registration: {registration.contact_email}")
        raise HTTPException(status_code=400, detail="Company already registered with this email")
    
    company_id = secrets.token_urlsafe(16)
    api_key = f"prr_{secrets.token_urlsafe(32)}"  # Prefixed API key
    
    company = Company(
        id=company_id,
        name=registration.name,
        contact_email=registration.contact_email,
        api_key=api_key
    )
    
    db.add(company)
    db.commit()
    
    logger.info(f"Company registered: {registration.name} ({registration.contact_email})")
    
    return {
        "message": "Company registered successfully",
        "company_id": company_id,
        "api_key": api_key,
        "name": registration.name,
        "note": "Store this API key securely - it will not be shown again"
    }

@app.post("/v1/audit/log")
@limiter.limit("1000/hour")
async def log_audit_entry(request: Request, entry: AuditLogEntry,
                         credentials: HTTPAuthorizationCredentials = Depends(security),
                         db: Session = Depends(get_db)):
    """Companies can log their privacy rights compliance actions"""
    
    company = verify_company_api_key(credentials, db)
    client_info = get_client_info(request)
    
    audit_entry = AuditLog(
        id=secrets.token_urlsafe(16),
        company_id=company.id,
        user_token=entry.user_token,
        action=entry.action,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        metadata=entry.metadata or {}
    )
    
    db.add(audit_entry)
    db.commit()
    
    logger.info(f"Audit entry logged: {company.name} -> {entry.action}")
    
    return {"message": "Audit entry logged successfully"}

@app.post("/v1/violations/report")
@limiter.limit("20/hour")
async def report_violation(request: Request, report: ViolationReport, db: Session = Depends(get_db)):
    """Users can report privacy violations"""
    
    # Verify the user token exists
    try:
        verify_user_token(report.user_token)
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid user token")
    
    client_info = get_client_info(request)
    
    audit_entry = AuditLog(
        id=secrets.token_urlsafe(16),
        company_id=None,  # No company associated with violation reports
        user_token=report.user_token,
        action="violation_reported",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        metadata={
            "company_name": report.company_name,
            "violation_type": report.violation_type,
            "description": report.description,
            "evidence_url": report.evidence_url,
            "reported_at": client_info["timestamp"]
        }
    )
    
    db.add(audit_entry)
    db.commit()
    
    logger.warning(f"Privacy violation reported: {report.company_name} -> {report.violation_type}")
    
    return {
        "message": "Violation reported successfully",
        "report_id": audit_entry.id,
        "next_steps": "Your report has been logged and will be included in transparency reports"
    }

@app.get("/v1/transparency/company/{company_id}")
async def get_company_transparency(company_id: str, db: Session = Depends(get_db)):
    """Public transparency endpoint - show company compliance stats"""
    
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get audit stats
    total_lookups = db.query(AuditLog).filter(
        AuditLog.company_id == company_id,
        AuditLog.action == "lookup_success"
    ).count()
    
    blocked_lookups = db.query(AuditLog).filter(
        AuditLog.company_id == company_id,
        AuditLog.action == "lookup_blocked_doxxing"
    ).count()
    
    recent_lookups = db.query(AuditLog).filter(
        AuditLog.company_id == company_id,
        AuditLog.action == "lookup_success",
        AuditLog.timestamp >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    violations_reported = db.query(AuditLog).filter(
        AuditLog.action == "violation_reported",
        AuditLog.metadata.contains({"company_name": company.name})
    ).count()
    
    return {
        "company_name": company.name,
        "company_id": company_id,
        "total_lookups": total_lookups,
        "blocked_lookups": blocked_lookups,
        "recent_lookups_30d": recent_lookups,
        "violations_reported": violations_reported,
        "compliance_score": max(0, 100 - (violations_reported * 10)),
        "registered_since": company.created_at.isoformat(),
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/v1/transparency/global")
async def get_global_transparency(db: Session = Depends(get_db)):
    """Global transparency statistics"""
    
    total_users = db.query(User).count()
    total_companies = db.query(Company).count()
    total_lookups = db.query(AuditLog).filter(AuditLog.action == "lookup_success").count()
    blocked_lookups = db.query(AuditLog).filter(AuditLog.action == "lookup_blocked_doxxing").count()
    total_violations = db.query(AuditLog).filter(AuditLog.action == "violation_reported").count()
    
    # Users with anti-doxxing protection
    users_with_protection = db.query(User).filter(
        User.rights.contains({"anti_doxxing": True})
    ).count()
    
    return {
        "total_users": total_users,
        "total_companies": total_companies,
        "total_lookups": total_lookups,
        "blocked_lookups": blocked_lookups,
        "protection_rate": round((blocked_lookups / max(total_lookups + blocked_lookups, 1)) * 100, 2),
        "users_with_anti_doxxing": users_with_protection,
        "anti_doxxing_adoption": round((users_with_protection / max(total_users, 1)) * 100, 2),
        "violations_reported": total_violations,
        "registry_effectiveness": "Reducing privacy violations through legal liability",
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/v1/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)