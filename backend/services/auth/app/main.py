"""
DeepTrust Authentication Service
================================
This service manages user identity, lifecycle, and secure access tokens. 
It utilizes a PostgreSQL backend for persistence and implements the OAuth2 
password flow with JWT (JSON Web Tokens).

Key Features:
- Secure password hashing using industry-standard algorithms (Bcrypt/Argon2).
- RBAC (Role-Based Access Control) for administrative operations.
- Health monitoring and database connectivity verification.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import os

# Import shared modules for consistency across microservices
from shared.database.base import get_db, init_db, check_db_connection
from shared.models import User, UserRole
from shared.schemas import (
    UserRegister, UserResponse, Token, UserUpdate,
    PasswordChange, MessageResponse, HealthResponse
)
from shared.utils import hash_password, verify_password, create_access_token, verify_token

app = FastAPI(
    title="DeepTrust Auth Service",
    description="Identity provider and session management for the DeepTrust platform.",
    version="1.0.0"
)

# Standard CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 authentication scheme declaration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# Token expiration configurable via environment variable; defaults to 30 minutes.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


@app.on_event("startup")
async def startup():
    """ Initialize database connections and schemas on service startup. """
    print("Initiating Auth Service sequence...")
    init_db()
    if check_db_connection():
        print("Database connectivity verified.")
    else:
        print("Critical Error: Database unreachable during initialization.")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to retrieve and validate the authenticated user from a JWT token.
    
    Args:
        token (str): The bearer token provided in the Authorization header.
        db (Session): The database session.
        
    Returns:
        User: The authenticated user profile.
        
    Raises:
        HTTPException: 401 if the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate security credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decrypt and verify the integrity of the JWT
        payload = verify_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Cross-reference the token against the persistent user database
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    return user


@app.get("/", response_model=MessageResponse)
async def root():
    """ Information endpoint for the Auth Service. """
    return {"message": "DeepTrust Auth Service", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse)
async def health():
    """ Health check verifying both service uptime and database state. """
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "degraded",
        "service": "auth",
        "version": "1.0.0",
        "database": "connected" if db_status else "disconnected"
    }


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new user in the system.
    
    Args:
        user_data (UserRegister): Registration details (username, email, password, etc.).
        
    Returns:
        User: The newly created user object.
        
    Raises:
        HTTPException: 400 if the username or email is already taken.
    """
    # Duplicate identifier checks
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create new user record with securely hashed password
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

    print(f"New user registered: {user.username}")
    return user


@app.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login endpoint.
    
    Validates credentials and returns a secure JWT access token.
    
    Args:
        form_data: standard OAuth2 login form containing username and password.
        
    Returns:
        dict: Access token and associated metadata.
    """
    # Locate user by either username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    # Validate existence and password hash
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Prevent access for deactivated accounts
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is currently inactive")

    # Audit login time
    user.last_login = datetime.utcnow()
    db.commit()

    # Generate JWT with embedded claims
    token = create_access_token(data={
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role.value
    })

    print(f"User successful login: {user.username}")

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@app.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """ Retrieves the profile of the currently authenticated user. """
    return current_user


@app.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the profile information of the current user.
    
    Supports partial updates of email and full name. Handles email uniqueness validation.
    """
    if update_data.email:
        # Prevent taking an email that belongs to another registered user
        if db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first():
            raise HTTPException(status_code=400, detail="Email already in use by another account")
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
    """
    Secure password rotation endpoint.
    Verifies the current password before applying the new hash.
    """
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Provided current password is incorrect")

    current_user.hashed_password = hash_password(password_data.new_password)
    db.commit()

    return {"message": "User password updated successfully"}


@app.delete("/me", response_model=MessageResponse)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Soft-deletes the current user's account by marking it as inactive.
    Retains data for compliance but prevents further authentication.
    """
    current_user.is_active = False
    db.commit()
    print(f"Self-deactivation processed for: {current_user.username}")
    return {"message": "Account deactivated successfully"}


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Administrative endpoint to list all registered users.
    Requires ADMIN privilege level.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrative privileges required")

    return db.query(User).offset(skip).limit(limit).all()


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Administrative endpoint to retrieve a specific user by UUID.
    Requires ADMIN privilege level.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrative privileges required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Requested user could not be found")

    return user


if __name__ == "__main__":
    import uvicorn
    # Local development server entry point on port 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)