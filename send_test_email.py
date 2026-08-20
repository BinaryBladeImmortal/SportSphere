from flask import Flask
from mail import send_email
from config import Config

# Create a minimal Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize mail
from mail import mail
mail.init_app(app)

def send_test_email():
    recipient_email = 'testuser1@example.com'
    subject = 'Test Email from Sports League Management System'
    
    text_body = """
    Hello there!
    
    This is a test email from the Sports League Management System.
    
    If you're seeing this email, the email functionality is working correctly.
    
    Best regards,
    The Sports League Management Team
    """
    
    html_body = """
    <html>
      <body>
        <h2>Test Email from Sports League Management System</h2>
        <p>Hello there!</p>
        
        <p>This is a test email from the Sports League Management System.</p>
        
        <p>If you're seeing this email, the email functionality is <strong>working correctly</strong>.</p>
        
        <p>Best regards,<br>
        The Sports League Management Team</p>
      </body>
    </html>
    """
    
    with app.app_context():
        send_email(subject, [recipient_email], text_body, html_body)
        print(f"Test email sent to {recipient_email}")

if __name__ == '__main__':
    send_test_email()
