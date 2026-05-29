from fastapi import APIRouter, HTTPException, status, Depends
import random
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm

from models.user import UserCreate, UserResponse, ForgetPasswordRequest, ResetPasswordRequest
from core.database import user_collection, otp_collection
from core.security import get_password_hash
from datetime import datetime, timedelta 
from models.token import AccessToken
from core.config import settings
from core.security import create_access_token, verify_password
from api.deps import get_current_user, require_admin
from core.email import send_otp_email

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

@router.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    A protected route that returns the logged-in user's profile informations.
    Any authenticated user can access this.
    """

    return UserResponse(
        id=str(current_user["_id"]),
        first_name=current_user["first_name"],
        last_name=current_user["last_name"],
        date_of_birth=current_user.get("date_of_birth"),
        gender=current_user.get("gender"),
        email=current_user["email"],
        role=current_user["role"]
    )

@router.get("/admin-only")
async def test_admin_route(current_admin: dict = Depends(require_admin)):
    """
    Strictly protected route that will throw a 403 forbidden error
    unless the logged-in user has a role of 'admin' in the database.
    """
    return {
        "message": f"Welcome to control center, Admin {current_admin['first_name']}!"
    }

@router.post("/forgot-password")
async def forget_password(request: ForgetPasswordRequest):
    # 1. Look for the user
    user = await user_collection.find_one({"email": request.email})

    # SECURITY PRO TIP: Even if the email doesn't exist, we return a success message.
    # This prevents hackers from using this endpoint to guess registered emails!
    if not user:
        return {"message": "If that email is registered, an OTP has sent. If you don't see it, please check your spam folder."}
    
    # 2. Genarate a random 6-digit OTP and an expiration time.
    otp = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # 3. Save the OTP to MongoDB (using upsert so if they request twice, it will overwrite the old OTP)
    await otp_collection.update_one(
        {"email": request.email},
        {"$set": {"otp": otp, "expires_at": expires_at}},
        upsert=True
    )

    # 4. Send the email!
    await send_otp_email(to_email=request.email, otp=otp)

    return {"message": "If that email is registered, an OTP has sent. If you don't see it, please check your spam folder."}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    # 1. Find the OTP record in MongoDB
    otp_record = await otp_collection.find_one({
        "email": request.email,
        "otp": request.otp,
    })

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP or email"
        )
    
    # 2. Check if the OTP has expired
    if datetime.utcnow() > otp_record["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )
    
    # 3. Hash the new password and update the user's document.
    new_hashed_password = get_password_hash(request.new_password)
    await user_collection.update_one(
        {"email": request.email},
        {"$set": {"hashed_password": new_hashed_password}}
    )

    return {"message": "Password has been reset successfully. You can now log in with your new password."}