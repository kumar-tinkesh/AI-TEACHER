import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Settings:
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_teacher.db")
    
    # JWT & Cryptography Configurations
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", 
        "696b4bf2826cfc2db724b0ad4b8efc0f4f98df363725b8216c52a0a2df37b420"
    )
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

settings = Settings()
