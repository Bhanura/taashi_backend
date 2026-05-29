from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date

# This is the schema for creating a new user (what the frontend sends us)
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=6)

# This is the schema for returning user data (hiding the password!)
class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    email: EmailStr
    role: str

# This represents how the user is actually stored in MongoDB
class UserInDB(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    email: EmailStr
    hashed_password: str
    role: str

class ForgetPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(..., min_length=6)
    