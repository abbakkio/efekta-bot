import os
from dotenv import load_dotenv

load_dotenv()

# URLs
BASE_URL = os.getenv("EFEKTA_BASE_URL", "https://learn.better.efekta.com/gap/ui/self-study")
LOGIN_URL = os.getenv("EFEKTA_LOGIN_URL", "https://learn.better.efekta.com")

# Credentials
EMAIL = os.getenv("EFEKTA_EMAIL", "")
PASSWORD = os.getenv("EFEKTA_PASSWORD", "")

# Operation mode
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"

# Delays (seconds)
MIN_DELAY_SEC = float(os.getenv("MIN_DELAY_SEC", "0.0" if FAST_MODE else "1.5"))
MAX_DELAY_SEC = float(os.getenv("MAX_DELAY_SEC", "0.1" if FAST_MODE else "3.5"))

# Storage
STORAGE_STATE = os.getenv("EFEKTA_STORAGE_STATE", "session_state.json")
