from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.security.jwt import create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    # TODO: Replace with actual PostgreSQL database verification
    if request.email == "guest@smartstay.com" and request.password == "password":
        token = create_access_token({"sub": request.email, "role": "guest"})
        return TokenResponse(access_token=token, role="guest")
    
    if request.email == "staff@smartstay.com" and request.password == "password":
        token = create_access_token({"sub": request.email, "role": "staff"})
        return TokenResponse(access_token=token, role="staff")

    raise HTTPException(status_code=401, detail="Invalid credentials")