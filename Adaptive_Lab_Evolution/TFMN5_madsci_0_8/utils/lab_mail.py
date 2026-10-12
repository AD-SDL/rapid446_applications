import smtplib
from email.message import EmailMessage
import os

from dotenv import load_dotenv

# loads .env into environment
load_dotenv()

# Set up redis for exchange location lock
smtp_server = os.getenv("SMTP_SERVER")
smtp_port = os.getenv("SMTP_PORT")
sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")
receiver_email = os.getenv("RECEIVER_EMAIL")

def send_email(error_msg: str):
    msg = EmailMessage()
    msg["Subject"] = "446 ERROR"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.set_content(error_msg)

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


