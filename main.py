from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.auth import router as auth_router
from core.config import settings

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

@app.get("/")
async def root():
    return {"message": "Taashi Backend is up and running!"}
