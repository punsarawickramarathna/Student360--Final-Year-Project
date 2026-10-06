import os
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig

# Load environment variables from .env file if available
load_dotenv()

raw_username = os.getenv("MAIL_USERNAME", "punsarawikramarathna@gmail.com")
raw_password = os.getenv("MAIL_PASSWORD", "toek wubr iokc brlf")
raw_from = os.getenv("MAIL_FROM", "")

# Ensure MAIL_USERNAME and MAIL_PASSWORD are clean of leading/trailing spaces or quotes
MAIL_USERNAME = raw_username.strip().strip("'\"") if raw_username else "punsarawikramarathna@gmail.com"
MAIL_PASSWORD = raw_password.strip().strip("'\"") if raw_password else "toek wubr iokc brlf"
MAIL_FROM = raw_from.strip().strip("'\"") if raw_from else MAIL_USERNAME

MAIL_PORT = 465
MAIL_SERVER = "smtp.gmail.com"
MAIL_STARTTLS = False
MAIL_SSL_TLS = True

# Standard Gmail Direct SSL settings on Port 465
conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TIMEOUT=30
)