from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    MONGODB_URL: str
    DATABASE_NAME: str
    SECRET_KEY: str
    
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    ALGORITHM: str = "HS256"

    OTP_EXPIRE_MINUTES: int = 5

    class Config:
        env_file = ".env"

settings = Settings()