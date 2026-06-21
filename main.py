from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.auth import router as auth_router
from core.config import settings
from api.time_management import router as time_router

# Initialize FastAPI app
app = FastAPI(
    title="Taashi Backend API",
    description="Backend for Assistant Taashi",
    version="1.0.0"
)

# Configure CORS dynamically
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect our authentication routes to the main app
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(time_router, prefix="/api/time", tags=["Time Management"])

@app.get("/")
async def root():
    return {"message": "Taashi Backend is up and running!"}
