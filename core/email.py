import aiosmtplib
from email.message import EmailMessage
from core.config import settings

async def send_otp_email(to_email: str, otp: str):
    """Asynchronously sends an OTP email using Gmail's SMTP"""

    # Construct the email message
    message = EmailMessage()
    message["From"] = settings.SMTP_USERNAME
    message["To"] = to_email
    message["Subject"] = "Taashi - Your Password Reset OTP"

    message.set_content(
        f"Hello,\n\n"
        f"You requested a password reset for your Taashi account.\n\n"
        f"Your 6-digit OTP is: {otp}\n"
        f"This OTP will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n\n"
        f"If you did not request this, please ignore this email.\n"
        f"Do not share this OTP with anyone.\n\n"
        f"Best regards,\n"
        f"Taashi Team"
    )

#Send the email asynchronously without blocking the FastAPI event loop
    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=True
    )