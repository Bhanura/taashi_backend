from fastapi import APIRouter, HTTPException, status
from models.user import UserCreate, UserResponse
from core.database import user_collection
from core.security import get_password_hash
from datetime import datetime

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    # 1. check if the email is already registered in MongoDB
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # 2. Hash the password securely
    hashed_password = get_password_hash(user.password)

    # 3. prepare the data for the database
    user_db_dict = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_of_birth": datetime.combine(user.date_of_birth, datetime.min.time()),
        "gender": user.gender,
        "email": user.email,
        "hashed_password": hashed_password,
        "role": user.role
    }

    # 4. insert the new user into MongoDB
    result = await user_collection.insert_one(user_db_dict)

    # 5. return the response using our pydantic model
    return UserResponse(
        id=str(result.inserted_id),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user_db_dict["role"]        
    )

