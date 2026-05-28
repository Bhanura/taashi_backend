from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    MONGODB_URL: str
    DATABASE_NAME: str
    SECRET_KEY: str
    
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str

    class Config:
        env_file = ".env"

settings = Settings()