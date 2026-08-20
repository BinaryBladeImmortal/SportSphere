import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_direct_test_email():
    # Get email settings from .env
    smtp_server = os.getenv('MAIL_SERVER')
    smtp_port = int(os.getenv('MAIL_PORT'))
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    # Email details
    sender_email = username
    receiver_email = "testuser1@example.com"
    subject = "Direct SMTP Test"
    
    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    
    # Create the plain-text version of the message
    text = """
    This is a direct SMTP test email.
    If you're seeing this, direct SMTP is working.
    """
    
    # Create the HTML version of the message
    html = """
    <html>
      <body>
        <h2>Direct SMTP Test</h2>
        <p>This is a direct SMTP test email.</p>
        <p>If you're seeing this, <strong>direct SMTP is working</strong>.</p>
      </body>
    </html>
    """
    
    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    
    # Add HTML/plain-text parts to MIMEMultipart message
    message.attach(part1)
    message.attach(part2)
    
    try:
        print(f"Connecting to SMTP server: {smtp_server}:{smtp_port}")
        print(f"Using username: {username}")
        
        # Create a secure SSL/TLS connection to the SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()  # Can be omitted
        server.starttls()  # Secure the connection
        server.ehlo()  # Can be omitted
        
        print("Connected to SMTP server, attempting login...")
        server.login(username, password)
        print("Login successful")
        
        print(f"Sending email to: {receiver_email}")
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(f"Error type: {type(e)}")
    finally:
        if 'server' in locals():
            server.quit()

if __name__ == "__main__":
    send_direct_test_email() 