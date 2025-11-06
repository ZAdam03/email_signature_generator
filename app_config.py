import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AUTHORITY = os.getenv("AUTHORITY")
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    PORT = int(os.getenv("PORT", 5000))
    SCOPE = ["User.Read"]
    SESSION_TYPE = "filesystem"
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Session konfiguráció
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
