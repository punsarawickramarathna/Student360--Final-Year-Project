from fastapi import APIRouter
from pydantic import BaseModel
from fastapi_mail import FastMail, MessageSchema
from email_config import conf

router = APIRouter()


class EmailRequest(BaseModel):

    emails: list[str]

    subject: str

    body: str


@router.post("/send-email")

async def send_email(data: EmailRequest):

    message = MessageSchema(

        subject=data.subject,

        recipients=data.emails,

        body=data.body,

        subtype="html"


    )

    fm = FastMail(conf)

    await fm.send_message(message)

    return {

        "message": "Emails Sent Successfully"

    }