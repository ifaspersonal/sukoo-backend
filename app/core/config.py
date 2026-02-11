from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    PROJECT_NAME = "SUKOO POS API"
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

settings = Settings()