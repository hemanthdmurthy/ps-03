from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        description="Unique username used for login credentials",
        examples=["john_doe"]
    )
    email: EmailStr = Field(
        ..., 
        description="Unique email address for communication and account recovery",
        examples=["john.doe@placementintel.com"]
    )
    password: str = Field(
        ..., 
        min_length=6, 
        max_length=100, 
        description="Secure plaintext password of at least 6 characters",
        examples=["P@ssw0rd123!"]
    )
    role: Optional[str] = Field(
        "viewer", 
        description="Assigned platform role determining authorization limits. Options: admin, researcher, viewer",
        examples=["researcher"]
    )

class UserLoginRequest(BaseModel):
    username: str = Field(
        ..., 
        description="Registered unique username or email address",
        examples=["john_doe"]
    )
    password: str = Field(
        ..., 
        description="Plaintext account password",
        examples=["P@ssw0rd123!"]
    )

class UserResponse(BaseModel):
    id: str = Field(..., description="Unique user record identifier (UUID)", examples=["usr-9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"])
    username: str = Field(..., description="Unique platform username", examples=["john_doe"])
    email: str = Field(..., description="Registered email address", examples=["john.doe@placementintel.com"])
    role: str = Field(..., description="Assigned authorization role", examples=["researcher"])
    is_active: bool = Field(..., description="Flag indicating if the user account is active", examples=[True])
    created_at: datetime = Field(..., description="UTC Timestamp when the user account was registered")
    updated_at: datetime = Field(..., description="UTC Timestamp when the user profile was last updated")

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Stateless JWT Access Token for authenticating subsequent HTTP requests", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    refresh_token: str = Field(..., description="Secure refresh token used to obtain a new access/refresh token pair (rotation)", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field("bearer", description="Standard token type scheme prefix", examples=["bearer"])
    role: str = Field(..., description="Authorized role bound to the issued tokens", examples=["researcher"])
    username: str = Field(..., description="Username associated with the session", examples=["john_doe"])

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Active, valid refresh token issued during login or last rotation", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])

