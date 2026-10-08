from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import smtplib
from email.message import EmailMessage

router = APIRouter()

class NotifyRequest(BaseModel):
    emails: list[str]
    lecturer_name: str

@router.post("/notify-risk")
async def notify_risk_students(request: NotifyRequest):
    print(f"Received email list from frontend: {request.emails}")
    
    if not request.emails:
        raise HTTPException(status_code=400, detail="No emails provided")
    
    system_email = "student360.alerts@gmail.com" 
    system_password = "oelk riur ngnj onpe" 

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(system_email, system_password)

        for email in request.emails:
            print(f"Processing email address: {email}")
            if not email or "@" not in email:
                print(f"Skipping invalid email address: {email}")
                continue

            msg = EmailMessage()
            msg.set_content(
                f"Dear Student,\n\n"
                f"Your aggregate performance is below the required threshold (Risk). "
                f"Please meet your lecturer, {request.lecturer_name}, immediately to discuss your academic progress.\n\n"
                f"Thank you,\n"
                f"Student360 Automated System"
            )
            
            msg['Subject'] = f"Action Required: Academic Warning from {request.lecturer_name}"
            msg['From'] = system_email
            msg['To'] = email
            
            server.send_message(msg)
            print(f"Successfully sent email to: {email}")
        
        server.quit()
        return {"message": "Emails sent successfully!", "recipients": request.emails}
        
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))