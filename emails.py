from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import dotenv_values
from typing import List
from models import User
import jwt

config_credentials = dotenv_values(".env")

config = ConnectionConfig(
    MAIL_USERNAME=config_credentials["EMAIL"],
    MAIL_PASSWORD=config_credentials["PASS"],
    MAIL_FROM=config_credentials["EMAIL"],
    MAIL_PORT=465,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


async def send_email(email: List, instance: User):
    token_data = {
        "id": instance.id,
        "email": instance.email
    }
    token = jwt.encode(token_data, config_credentials["SECRET"], algorithm="HS256")
    email_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Confirmation</title>
    </head>
    <body>
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h1 style="text-align: center; color: #007bff;">Confirm Your Email Address</h1>
            <p>Dear {instance.username},</p>
            <p>Thank you for registering with ShahraZad! To complete your registration and confirm your email address, please click on the following link:</p>
            <p><a href="http://localhost:8000/auth/verification?token={token}" style="display: block; width: fit-content; margin: 20px auto; padding: 10px 20px; background-color: #007bff; color: #fff; text-decoration: none;">Confirm Email</a></p>
            <p>Please note that this link will expire in [Expiration Time], so be sure to complete the confirmation process as soon as possible.</p>
            <p>If you did not register with ShahraZad, please disregard this email.</p>
            <p>Thank you,<br>ShahraZad Team</p>
        </div>
    </body>
    </html>
    """

    message = MessageSchema(
        subject="ShahraZad Account Verification",
        recipients=email,  # Provide a list of email addresses
        body=email_template,
        subtype=MessageType.html
    )

    fn = FastMail(config)
    await fn.send_message(message)