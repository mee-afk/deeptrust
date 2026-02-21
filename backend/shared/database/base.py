"""
Production-grade database configuration for all microservices.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://deeptrust:deeptrust_dev_password@postgres:5432/deeptrust"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    pool_recycle=3600,
    pool_timeout=30,
    echo=False,
    connect_args={
        "connect_timeout": 10,
        "options": "-c timezone=utc"
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()


def get_db():
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    try:
        # Import here to avoid circular imports
        # These imports register models with SQLAlchemy Base
        from shared.models.user import User
        from shared.models.analysis import Analysis
        from shared.models.analysis_result import AnalysisResult
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


def check_db_connection() -> bool:
    """Health check for database connectivity."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


def drop_all_tables():
    """Drop all tables. DEVELOPMENT ONLY."""
    if os.getenv("ENV") == "production":
        raise RuntimeError("❌ Cannot drop tables in production")
    Base.metadata.drop_all(bind=engine)
    logger.warning("⚠️  All database tables dropped")


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("Database connection established")