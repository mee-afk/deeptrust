"""
DeepTrust Authentication Service
Production-grade implementation using shared modules.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import os

from shared.database.base import get_db, init_db, check_db_connection
from shared.models import User, UserRole
from shared.schemas import (
    UserRegister, UserResponse, Token, UserUpdate,
    PasswordChange, MessageResponse, HealthResponse
)
from shared.utils import hash_password, verify_password, create_access_token, verify_token

app = FastAPI(
    title="DeepTrust Auth Service",
    description="Enterprise authentication and user management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


@app.on_event("startup")
async def startup():
    print("🚀 Starting Auth Service...")
    init_db()
    if check_db_connection():
        print("✅ Database connected")
    else:
        print("❌ Database connection failed")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    return user


@app.get("/", response_model=MessageResponse)
async def root():
    return {"message": "DeepTrust Auth Service", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse)
async def health():
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "degraded",
        "service": "auth",
        "version": "1.0.0",
        "database": "connected" if db_status else "disconnected"
    }


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=UserRole.USER
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(f"✅ User registered: {user.username}")
    return user


@app.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account inactive")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(data={
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role.value
    })

    print(f"✅ User logged in: {user.username}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@app.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@app.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if update_data.email:
        if db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = update_data.email

    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/me/password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password incorrect")

    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}


@app.delete("/me", response_model=MessageResponse)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.is_active = False
    db.commit()
    print(f"⚠️  Account deactivated: {current_user.username}")
    return {"message": "Account deactivated successfully"}


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin required")

    return db.query(User).offset(skip).limit(limit).all()


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)