from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

from storage import create_user, authenticate_user_by_email, get_user_by_id
from config.security import create_access_token, decode_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ---- Schemas ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    username: Optional[str] = None  # accepted but ignored server-side

class UserPublic(BaseModel):
    id: int
    email: EmailStr

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginBody(BaseModel):
    email: EmailStr
    password: str

# ---- Current user dependency ----
def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    u = get_user_by_id(sub)
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserPublic(id=u.id, email=u.email)

# ---- Routes ----
@router.post("/signup", response_model=UserPublic, status_code=201, summary="Register a new user")
def signup(body: UserCreate):
    try:
        created = create_user(username=body.username, password=body.password, email=body.email)
        # created returns dict with id, email, created_at
        return {"id": created["id"], "email": created["email"]}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/login", response_model=TokenResponse, summary="Login and get JWT (OAuth2 form)")
def login(form: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm provides 'username' and 'password'.
    # We interpret 'username' as the EMAIL.
    user = authenticate_user_by_email(email=form.username, password=form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login_json", response_model=TokenResponse, summary="Login with JSON body")
def login_json(body: LoginBody):
    user = authenticate_user_by_email(email=body.email, password=body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserPublic, summary="Get current user profile")
def me(current: UserPublic = Depends(get_current_user)):
    return current
