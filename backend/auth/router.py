from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth.utils import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()

@router.post("/register", response_model=schemas.MessageResponse, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Create user
    user = models.User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        career_goal=payload.career_goal,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": f"Account created successfully! Welcome, {user.first_name}."}


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login and receive a JWT token."""
    user = db.query(models.User).filter(models.User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Get current logged-in user's profile."""
    return current_user


@router.post("/logout", response_model=schemas.MessageResponse)
def logout():
    """Logout (frontend should delete the token)."""
    return {"message": "Logged out successfully."}