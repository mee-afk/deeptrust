import sys
sys.path.append('.')

from sqlalchemy import create_engine
from shared.database.base import Base
import os

# Import all models here
# from services.auth.app.models import User
# from services.analysis.app.models import Analysis

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://deeptrust:password@localhost/deeptrust")

engine = create_engine(DATABASE_URL)

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✓ Database initialized successfully!")
