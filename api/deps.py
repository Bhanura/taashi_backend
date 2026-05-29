from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from core.config import settings
from core.database import user_collection
from models.token import TokenData

# This tells FastAPI to look for a 'Authentication : Bearer <token>' header.
# Its points to our login URL so the documentations knows where to fetch tokens.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decodes the JWT token, extracts the user, and ensures they exist in the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the JWT token using our secret key and algorithm
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")

        if email is None or role is None:
            raise credentials_exception
        
        token_data = TokenData(email=email, role=role)
    except jwt.PyJWTError:
        raise credentials_exception

    # Look up the user in the database by email
    user = await user_collection.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception

    return user

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Ensure that the current authenticated user has an admin role.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    return current_user