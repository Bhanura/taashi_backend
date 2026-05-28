from passlib.context import CryptContext

# Tell passlib to use the argon2 hashing algorithm
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verfy_password(plain_password: str, hashed_password: str) -> bool:
    """check if a provided password matches the hashed version"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """hash a password for storing in the database"""
    return pwd_context.hash(password)