from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from models.user import UserCreate, UserResponse
from core.database import user_collection
from core.security import get_password_hash
from datetime import datetime, timedelta 
from models.token import AccessToken
from core.config import settings
from core.security import create_access_token, verify_password

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

    # BUG FIX: Safely check if the date exists before converting
    dob_datetime = None
    if user.date_of_birth:
        dob_datetime = datetime.combine(user.date_of_birth, datetime.min.time())

    # 3. prepare the data for the database
    user_db_dict = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_of_birth": dob_datetime,
        "gender": user.gender,
        "email": user.email,
        "hashed_password": hashed_password,
        "role": "user"
    }

    # 4. insert the new user into MongoDB
    result = await user_collection.insert_one(user_db_dict)

    # 5. return the response using our pydantic model
    return UserResponse(
        id=str(result.inserted_id),
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        email=user.email,
        role=user_db_dict["role"]        
    )

@router.post("/login", response_model=AccessToken)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. look up user by email
    # (note: form_data.username contains the email from the frontend)
    user = await user_collection.find_one({"email": form_data.username})

    # 2. check if user exists and if the password matches the argon2 hash
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. create the JWT token containing the user's email and role, with an expiration time
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]},
        expires_delta=access_token_expires
    )

    # 4. return the token to the frontend
    return AccessToken(access_token=access_token, token_type="bearer")