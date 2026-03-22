"""
SIRA Platform Backend Implementation (MVP Phase 1)

Based on PRD for SIRA (Shipping Intelligence & Risk Analytics)
Sponsor: Energie Partners (EP)
Focus: Digital Control Tower + Security Intelligence MVP
Stack: Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy 2.0
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import sessionmaker, relationship, Session, declarative_base
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import jwt
from jwt.exceptions import InvalidTokenError
import os
import hashlib
from passlib.context import CryptContext
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/sira_db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SQLAlchemy setup
# SQLite doesn't support pool_size/max_overflow; handle both DB types
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== Database Models ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # operator, security_lead, supervisor, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Movement(Base):
    __tablename__ = "movements"
    
    id = Column(Integer, primary_key=True, index=True)
    cargo = Column(String(255), nullable=False)
    route = Column(Text, nullable=False)
    assets = Column(Text)
    stakeholders = Column(Text)
    laycan_start = Column(DateTime(timezone=True), nullable=False)
    laycan_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    events = relationship("Event", back_populates="movement", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="movement")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    movement_id = Column(Integer, ForeignKey("movements.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    location = Column(String(255))
    actor = Column(String(255))
    evidence = Column(Text)  # JSON or reference to evidence
    event_type = Column(String(50))  # planned, actual, security, operational
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    movement = relationship("Movement", back_populates="events")


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String(20), nullable=False)  # Critical/High/Medium/Low
    confidence = Column(Float, nullable=False)
    sla_timer = Column(Integer)  # minutes
    domain = Column(String(100))
    site_zone = Column(String(100))
    movement_id = Column(Integer, ForeignKey("movements.id"), nullable=True)
    status = Column(String(50), default="open")  # open/acknowledged/assigned/closed
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    movement = relationship("Movement", back_populates="alerts")
    case = relationship("Case", back_populates="alerts")


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    overview = Column(Text)
    timeline = Column(Text)  # JSON of events
    actions = Column(Text)  # JSON of actions
    evidence_refs = Column(Text)  # JSON of evidence references
    costs = Column(Float, default=0.0)
    parties = Column(Text)
    audit = Column(Text)
    status = Column(String(50), default="open")
    closure_code = Column(String(100))
    priority = Column(String(20), default="medium")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    alerts = relationship("Alert", back_populates="case")
    evidences = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")


class Playbook(Base):
    __tablename__ = "playbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_type = Column(String(100), nullable=False)
    domain = Column(String(100))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    steps = Column(Text, nullable=False)  # JSON array of steps
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class Evidence(Base):
    __tablename__ = "evidences"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(50), nullable=False)  # IoT/photo/video/document/etc.
    file_ref = Column(String(500))  # S3 path or local reference
    metadata = Column(Text)  # JSON: uploader, timestamp, location
    verification_status = Column(String(50), default="pending")
    file_hash = Column(String(64))  # SHA-256 for integrity
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    case = relationship("Case", back_populates="evidences")


# Create tables
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


# ==================== Pydantic Schemas ====================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(operator|security_lead|supervisor|admin)$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class MovementCreate(BaseModel):
    cargo: str = Field(..., min_length=1, max_length=255)
    route: str = Field(..., min_length=1)
    assets: Optional[str] = None
    stakeholders: Optional[str] = None
    laycan_start: datetime
    laycan_end: datetime


class MovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    cargo: str
    route: str
    assets: Optional[str]
    stakeholders: Optional[str]
    laycan_start: datetime
    laycan_end: datetime
    status: str
    created_at: datetime


class EventCreate(BaseModel):
    movement_id: int = Field(..., gt=0)
    timestamp: datetime
    location: Optional[str] = Field(None, max_length=255)
    actor: Optional[str] = Field(None, max_length=255)
    evidence: Optional[str] = None
    event_type: str = Field(..., pattern="^(planned|actual|security|operational)$")
    description: Optional[str] = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    movement_id: int
    timestamp: datetime
    location: Optional[str]
    actor: Optional[str]
    event_type: str
    description: Optional[str]
    created_at: datetime


class AlertCreate(BaseModel):
    severity: str = Field(..., pattern="^(Critical|High|Medium|Low)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    sla_timer: Optional[int] = Field(None, gt=0)
    domain: Optional[str] = Field(None, max_length=100)
    site_zone: Optional[str] = Field(None, max_length=100)
    movement_id: Optional[int] = None
    description: Optional[str] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    severity: str
    confidence: float
    sla_timer: Optional[int]
    domain: Optional[str]
    site_zone: Optional[str]
    movement_id: Optional[int]
    status: str
    description: Optional[str]
    created_at: datetime


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    overview: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    overview: Optional[str]
    status: str
    priority: str
    costs: float
    created_at: datetime
    updated_at: Optional[datetime]


class PlaybookCreate(BaseModel):
    incident_type: str = Field(..., min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    steps: str  # JSON string


class PlaybookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    incident_type: str
    domain: Optional[str]
    title: str
    description: Optional[str]
    is_active: bool
    created_at: datetime


class EvidenceCreate(BaseModel):
    case_id: int = Field(..., gt=0)
    evidence_type: str = Field(..., max_length=50)
    file_ref: str = Field(..., max_length=500)
    metadata: Optional[str] = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    case_id: int
    evidence_type: str
    file_ref: str
    verification_status: str
    file_hash: Optional[str]
    created_at: datetime


# ==================== Database Dependency ====================

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ==================== Authentication Utils ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


def require_role(allowed_roles: List[str]):
    """Dependency to check user role"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# ==================== FastAPI Application ====================

app = FastAPI(
    title="SIRA Platform API",
    description="MVP for Shipping Intelligence & Risk Analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("SIRA Platform API started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("SIRA Platform API shutting down")


# ==================== Health Check ====================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== Authentication Endpoints ====================

@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Create a new user (Admin only)"""
    # Check if username exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email exists
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User created: {user.username}")
    return db_user


@app.post("/token", response_model=Token, tags=["Authentication"])
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login to obtain access token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserResponse, tags=["Authentication"])
def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# ==================== Movements API ====================

@app.post("/movements/", response_model=MovementResponse, status_code=status.HTTP_201_CREATED, tags=["Movements"])
def create_movement(
    movement: MovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["operator", "supervisor", "admin"]))
):
    """Create a new movement"""
    if movement.laycan_start >= movement.laycan_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="laycan_start must be before laycan_end"
        )
    
    db_movement = Movement(**movement.model_dump())
    db.add(db_movement)
    db.commit()
    db.refresh(db_movement)
    logger.info(f"Movement created: ID {db_movement.id}")
    return db_movement


@app.get("/movements/{movement_id}", response_model=MovementResponse, tags=["Movements"])
def get_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get movement by ID"""
    movement = db.query(Movement).filter(Movement.id == movement_id).first()
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movement not found"
        )
    return movement


@app.get("/movements/", response_model=List[MovementResponse], tags=["Movements"])
def list_movements(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all movements with optional filtering"""
    query = db.query(Movement)
    if status:
        query = query.filter(Movement.status == status)
    movements = query.offset(skip).limit(limit).all()
    return movements


# ==================== Events API ====================

@app.post("/events/", response_model=EventResponse, status_code=status.HTTP_201_CREATED, tags=["Events"])
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ingest a new event"""
    # Verify movement exists
    movement = db.query(Movement).filter(Movement.id == event.movement_id).first()
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movement not found"
        )
    
    db_event = Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    logger.info(f"Event created: ID {db_event.id} for Movement {event.movement_id}")
    
    # TODO: Trigger alert derivation for security events
    if event.event_type == "security":
        logger.warning(f"Security event detected: {db_event.id}")
    
    return db_event


@app.get("/events/", response_model=List[EventResponse], tags=["Events"])
def list_events(
    movement_id: Optional[int] = None,
    event_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List events with optional filtering"""
    query = db.query(Event)
    if movement_id:
        query = query.filter(Event.movement_id == movement_id)
    if event_type:
        query = query.filter(Event.event_type == event_type)
    events = query.offset(skip).limit(limit).all()
    return events


# ==================== Alerts API ====================

@app.post("/alerts/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED, tags=["Alerts"])
def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Create a new alert"""
    if alert.movement_id:
        movement = db.query(Movement).filter(Movement.id == alert.movement_id).first()
        if not movement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movement not found"
            )
    
    db_alert = Alert(**alert.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    logger.info(f"Alert created: ID {db_alert.id}, Severity: {alert.severity}")
    return db_alert


@app.get("/alerts/", response_model=List[AlertResponse], tags=["Alerts"])
def list_alerts(
    domain: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List alerts with optional filtering"""
    query = db.query(Alert)
    if domain:
        query = query.filter(Alert.domain == domain)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    alerts = query.offset(skip).limit(limit).all()
    return alerts


@app.put("/alerts/{alert_id}/status", tags=["Alerts"])
def update_alert_status(
    alert_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update alert status"""
    if new_status not in ["open", "acknowledged", "assigned", "closed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status"
        )
    
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.status = new_status
    alert.updated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Alert {alert_id} status updated to {new_status}")
    return {"message": "Alert status updated", "alert_id": alert_id, "status": new_status}


# ==================== Cases API ====================

@app.post("/cases/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED, tags=["Cases"])
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Create a new case"""
    db_case = Case(**case.model_dump())
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    logger.info(f"Case created: ID {db_case.id}")
    return db_case


@app.get("/cases/{case_id}", response_model=CaseResponse, tags=["Cases"])
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get case by ID"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    return case


@app.get("/cases/", response_model=List[CaseResponse], tags=["Cases"])
def list_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List cases with optional filtering"""
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status)
    if priority:
        query = query.filter(Case.priority == priority)
    cases = query.offset(skip).limit(limit).all()
    return cases


@app.put("/cases/{case_id}/close", tags=["Cases"])
def close_case(
    case_id: int,
    closure_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Close a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    case.status = "closed"
    case.closure_code = closure_code
    case.closed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Case {case_id} closed with code: {closure_code}")
    return {"message": "Case closed successfully", "case_id": case_id, "closure_code": closure_code}


# ==================== Playbooks API ====================

@app.post("/playbooks/", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED, tags=["Playbooks"])
def create_playbook(
    playbook: PlaybookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "admin"]))
):
    """Create a new playbook"""
    db_playbook = Playbook(**playbook.model_dump())
    db.add(db_playbook)
    db.commit()
    db.refresh(db_playbook)
    logger.info(f"Playbook created: ID {db_playbook.id}")
    return db_playbook


@app.get("/playbooks/", response_model=List[PlaybookResponse], tags=["Playbooks"])
def list_playbooks(
    incident_type: Optional[str] = None,
    domain: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List playbooks with optional filtering"""
    query = db.query(Playbook).filter(Playbook.is_active == is_active)
    if incident_type:
        query = query.filter(Playbook.incident_type == incident_type)
    if domain:
        query = query.filter(Playbook.domain == domain)
    playbooks = query.all()
    return playbooks


# ==================== Evidence API ====================

@app.post("/evidences/", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED, tags=["Evidence"])
def upload_evidence(
    evidence: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload evidence for a case"""
    # Verify case exists
    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Compute hash for integrity
    evidence_hash = hashlib.sha256(evidence.file_ref.encode()).hexdigest()
    
    db_evidence = Evidence(
        **evidence.model_dump(),
        file_hash=evidence_hash,
        uploaded_by=current_user.id
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    logger.info(f"Evidence uploaded: ID {db_evidence.id} for Case {evidence.case_id}")
    
    # TODO: Phase 3 - Anchor to blockchain
    
    return db_evidence


@app.get("/evidences/case/{case_id}", response_model=List[EvidenceResponse], tags=["Evidence"])
def list_case_evidence(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all evidence for a case"""
    # Verify case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    return evidences


# ==================== Export API ====================

@app.get("/cases/{case_id}/export", tags=["Export"])
def export_compliance_pack(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["security_lead", "supervisor", "admin"]))
):
    """Export compliance pack for a case"""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Get related data
    alerts = db.query(Alert).filter(Alert.case_id == case_id).all()
    evidences = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    
    # TODO: Implement actual PDF/ZIP generation with weasyprint or reportlab
    export_data = {
        "case": {
            "id": case.id,
            "title": case.title,
            "overview": case.overview,
            "status": case.status,
            "priority": case.priority,
            "costs": case.costs,
            "created_at": case.created_at.isoformat() if case.created_at else None,
        },
        "alerts_count": len(alerts),
        "evidences_count": len(evidences),
        "export_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(f"Compliance pack exported for Case {case_id}")
    return {
        "message": "Compliance pack ready for export",
        "data": export_data,
        "format": "JSON (PDF/ZIP generation pending)"
    }


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
