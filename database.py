from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DATABASE_URL

Base = declarative_base()

# Lazy initialization - don't connect during build phase
_engine = None
_SessionLocal = None

def get_engine():
    """Get or create the database engine lazily."""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)
        except Exception as e:
            print(f"Warning: Could not create engine: {e}", flush=True)
            # Return None and let the error propagate when actually needed
            raise
    return _engine

def get_SessionLocal():
    """Get or create the session factory lazily."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

class LazySessionLocal:
    """Callable wrapper that provides SessionLocal() syntax with lazy initialization."""
    def __call__(self):
        return get_SessionLocal()()

# Export as SessionLocal for backward compatibility
SessionLocal = LazySessionLocal()


class Lead(Base):
    __tablename__ = 'leads'

    id = Column(String, primary_key=True, index=True)  # UUID or auto-generated
    name = Column(String, index=True, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    location = Column(String, nullable=True)
    city = Column(String, index=True, nullable=True)
    state = Column(String, nullable=True)

    # Qualification & Notes
    qualification = Column(String, index=True, default='unqualified')  # good/medium/low/unqualified
    setter_notes = Column(String, nullable=True)  # What to bring up on call

    # Call Tracking
    call_status = Column(String, default='not_contacted')  # not_contacted/attempted/connected/converted/declined
    call_outcome = Column(String, nullable=True)  # Notes from the call
    attempts = Column(Integer, default=0)
    last_contact_attempt = Column(DateTime, nullable=True)

    # Legacy fields (kept for compatibility)
    website = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True, default=0)
    address = Column(String, nullable=True)
    category = Column(String, index=True, nullable=True)

    # Flags
    no_website = Column(Boolean, default=False, index=True)
    low_reviews = Column(Boolean, default=False, index=True)
    possibly_inactive = Column(Boolean, default=False, index=True)

    # Metadata
    priority_score = Column(Float, default=0.0)
    added_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    follow_up_date = Column(DateTime, nullable=True)

    def __repr__(self):
        return f'<Lead(id={self.id}, name={self.name}, qualification={self.qualification})>'


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=get_engine())


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
