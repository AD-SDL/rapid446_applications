import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"  
SMTP_PORT = 465                 
SENDER_EMAIL = "446automatedlab@gmail.com"
SENDER_PASSWORD = "xufo ddhy gnob oqcf"
RECEIVER_EMAIL = "cstone@anl.gov"




def send_email(error_msg: str):
    msg = EmailMessage()
    msg["Subject"] = "446 ERROR"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg.set_content(error_msg)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


