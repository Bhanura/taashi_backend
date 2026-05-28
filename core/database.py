from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

# Initialize MongoDB client
client = AsyncIOMotorClient(settings.MONGODB_URL)

# Select the database
db = client[settings.DATABASE_NAME]

# Get the users collection
user_collection = db.get_collection("users")