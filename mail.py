from flask import current_app
from flask_mail import Mail, Message
from smtplib import SMTPAuthenticationError
from threading import Thread
import logging

mail = Mail()
logger = logging.getLogger(__name__)

def _email_is_configured(app):
    """Return whether the minimum SMTP settings are available."""
    return bool(
        app.config.get('MAIL_SERVER')
        and app.config.get('MAIL_USERNAME')
        and app.config.get('MAIL_PASSWORD')
        and app.config.get('MAIL_DEFAULT_SENDER')
        and app.config.get('MAIL_PASSWORD') != 'YOUR_APP_PASSWORD_HERE'
    )

def send_async_email(app, msg):
    with app.app_context():
        if not _email_is_configured(app):
            logger.warning('Email not configured - skipping email send')
            return False
        try:
            mail.send(msg)
            logger.info('Email sent successfully to %s', msg.recipients)
            return True
        except SMTPAuthenticationError:
            logger.warning(
                'Email authentication failed - skipping email send. '
                'Check MAIL_USERNAME and MAIL_PASSWORD.'
            )
            return False
        except Exception as e:
            logger.warning('Email send failed - skipping email send: %s', e)
            return False

def send_email(subject, recipients, text_body, html_body=None, sender=None, attachments=None):
    """
    Send an email with the given parameters
    
    Args:
        subject (str): Email subject
        recipients (list): List of recipient email addresses
        text_body (str): Plain text body of the email
        html_body (str, optional): HTML version of the email body. Defaults to None.
        sender (str, optional): Email sender address. If None, uses the default sender.
        attachments (list, optional): List of attachment tuples (filename, mimetype, data)
    """
    app = current_app._get_current_object()
    if not _email_is_configured(app):
        logger.warning('Email not configured - skipping email send')
        return False

    try:
        msg = Message(subject,
                      recipients=recipients,
                      body=text_body,
                      html=html_body,
                      sender=sender or app.config['MAIL_DEFAULT_SENDER'])
    except Exception as e:
        logger.warning('Email preparation failed - skipping email send: %s', e)
        return False
    
    # Add any attachments
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    
    # Send email asynchronously
    Thread(target=send_async_email, args=(app, msg), daemon=True).start()
    return True

# Example email templates
def send_welcome_email(user_email, username):
    """Send a welcome email to a newly registered user"""
    subject = "Welcome to the Sports League Management System"
    
    text_body = f"""
    Hello {username},
    
    Welcome to the Sports League Management System! Thank you for registering.
    
    With your account, you can:
    - Track your favorite teams and players
    - Get updates on upcoming matches
    - View league standings and statistics
    
    If you have any questions, please don't hesitate to contact us.
    
    Best regards,
    The Sports League Management Team
    """
    
    html_body = f"""
    <html>
      <body>
        <h2>Welcome to the Sports League Management System!</h2>
        <p>Hello <strong>{username}</strong>,</p>
        <p>Thank you for registering with us. We're excited to have you join our community!</p>
        
        <p>With your account, you can:</p>
        <ul>
          <li>Track your favorite teams and players</li>
          <li>Get updates on upcoming matches</li>
          <li>View league standings and statistics</li>
        </ul>
        
        <p>If you have any questions, please don't hesitate to contact us.</p>
        
        <p>Best regards,<br>
        The Sports League Management Team</p>
      </body>
    </html>
    """
    
    return send_email(subject, [user_email], text_body, html_body)

def send_match_reminder(user_email, username, match_details):
    """Send a match reminder email to user"""
    subject = f"Upcoming Match Reminder: {match_details['home_team']} vs {match_details['away_team']}"
    
    text_body = f"""
    Hello {username},
    
    This is a reminder about an upcoming match you might be interested in:
    
    {match_details['home_team']} vs {match_details['away_team']}
    Date: {match_details['date']}
    Time: {match_details['time']}
    Stadium: {match_details['stadium']}
    
    Don't miss it!
    
    Best regards,
    The Sports League Management Team
    """
    
    html_body = f"""
    <html>
      <body>
        <h2>Upcoming Match Reminder</h2>
        <p>Hello <strong>{username}</strong>,</p>
        
        <p>This is a reminder about an upcoming match you might be interested in:</p>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0;">
          <h3 style="color: #4361ee; margin-top: 0;">{match_details['home_team']} vs {match_details['away_team']}</h3>
          <p><strong>Date:</strong> {match_details['date']}</p>
          <p><strong>Time:</strong> {match_details['time']}</p>
          <p><strong>Stadium:</strong> {match_details['stadium']}</p>
        </div>
        
        <p>Don't miss it!</p>
        
        <p>Best regards,<br>
        The Sports League Management Team</p>
      </body>
    </html>
    """
    
    return send_email(subject, [user_email], text_body, html_body)

def send_password_reset(user_email, username, reset_link):
    """Send a password reset email to user"""
    subject = "Password Reset Request"
    
    text_body = f"""
    Hello {username},
    
    You recently requested to reset your password. Please click on the link below to reset it:
    
    {reset_link}
    
    If you did not request a password reset, please ignore this email.
    
    Best regards,
    The Sports League Management Team
    """
    
    html_body = f"""
    <html>
      <body>
        <h2>Password Reset Request</h2>
        <p>Hello <strong>{username}</strong>,</p>
        
        <p>You recently requested to reset your password. Please click on the button below to reset it:</p>
        
        <p style="text-align: center; margin: 25px 0;">
          <a href="{reset_link}" style="background-color: #4361ee; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
        </p>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all;">
          {reset_link}
        </p>
        
        <p>If you did not request a password reset, please ignore this email.</p>
        
        <p>Best regards,<br>
        The Sports League Management Team</p>
      </body>
    </html>
    """
    
    return send_email(subject, [user_email], text_body, html_body)