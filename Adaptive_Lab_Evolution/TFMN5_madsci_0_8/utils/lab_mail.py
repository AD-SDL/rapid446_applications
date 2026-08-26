import smtplib
from email.message import EmailMessage

# 1. Configure configuration and credentials
SMTP_SERVER = "smtp.gmail.com"  
SMTP_PORT = 465                 
SENDER_EMAIL = "446automatedlab@gmail.com"
SENDER_PASSWORD = "xufo ddhy gnob oqcf"
RECEIVER_EMAIL = "cstone@anl.gov"

# 2. Construct the email message
msg = EmailMessage()
msg["Subject"] = "TESTING"
msg["From"] = SENDER_EMAIL
msg["To"] = RECEIVER_EMAIL
msg.set_content("HELLO THIS IS ABE I AM TESTING THE EMAIL SCRIPT")

# 3. Connect to the server and send
try:
    # Use SMTP_SSL for port 465
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
    print("Email sent successfully!")
except Exception as e:
    print(f"Failed to send email: {e}")
