from fastapi import FastAPI
from api.auth import router as auth_router

# Initialize FastAPI app
app = FastAPI(
    title="Taashi Backend API",
    description="Backend for Assistant Taashi",
    version="1.0.0"
)

# Connect our authentication routes to the main app
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {"message": "Taashi Backend is up and running!"}
