import re
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi_mail import FastMail, MessageSchema
from email_config import conf

logger = logging.getLogger(__name__)

router = APIRouter()


class EmailRequest(BaseModel):
    emails: list[str]
    subject: str
    body: str


EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)


def is_valid_email(email_str: str) -> bool:
    if not email_str or not isinstance(email_str, str):
        return False
    return bool(EMAIL_REGEX.match(email_str.strip()))


@router.post("/send-email")
async def send_email(data: EmailRequest):
    fm = FastMail(conf)
    success_count = 0
    failed_emails = []

    # Clean and deduplicate recipient list
    raw_emails = data.emails or []
    cleaned_recipients = []
    seen = set()

    for item in raw_emails:
        if isinstance(item, str):
            clean = item.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                cleaned_recipients.append(clean)

    # Dispatch email per recipient inside a try-except loop
    for email_addr in cleaned_recipients:
        # Validate format using regex before attempting dispatch
        if not is_valid_email(email_addr):
            logger.warning("Skipping invalid email address format: %s", email_addr)
            failed_emails.append(email_addr)
            continue

        try:
            message = MessageSchema(
                subject=data.subject,
                recipients=[email_addr],
                body=data.body,
                subtype="html",
            )
            await fm.send_message(message)
            success_count += 1
            logger.info("Email sent successfully to %s", email_addr)
        except Exception as exc:
            logger.warning("Failed to send email to %s: %s", email_addr, exc)
            failed_emails.append(email_addr)

    failed_count = len(failed_emails)
    summary_message = (
        f"Emails sent successfully to {success_count} student(s). "
        f"{failed_count} invalid/failed emails were skipped."
    )

    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_emails": failed_emails,
        "message": summary_message,
    }