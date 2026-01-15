import os
from werkzeug.utils import secure_filename
from PIL import Image
import base64
from io import BytesIO
import random
import string
import re
from flask_mail import Mail, Message

mail = Mail()

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_base64_image(base64_string, upload_folder, filename_prefix='animal'):
    """Save base64 encoded image to file"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        
        # Generate unique filename
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.jpg"
        filepath = os.path.join(upload_folder, filename)
        
        # Resize image if too large (max 1200px width)
        max_width = 1200
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Save image
        image.save(filepath, 'JPEG', quality=85, optimize=True)
        
        return filename
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

def delete_file(filepath):
    """Delete a file if it exists"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Error deleting file: {e}")
    return False

def generate_verification_code():
    """Generate 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code, name):
    """Send verification code via email"""
    try:
        msg = Message(
            subject='NAAM - Your Verification Code',
            recipients=[email],
            body=f'''Hello {name},

Welcome to NAAM Farm Animal Tracker!

Your verification code is: {code}

This code will expire in 10 minutes.

Thank you,
NAAM Team
'''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_verification_sms(mobile, code, name):
    """Send verification code via SMS using Twilio"""
    try:
        from twilio.rest import Client
        from flask import current_app
        
        account_sid = current_app.config['TWILIO_ACCOUNT_SID']
        auth_token = current_app.config['TWILIO_AUTH_TOKEN']
        twilio_number = current_app.config['TWILIO_PHONE_NUMBER']
        
        if not account_sid or not auth_token:
            print("Twilio credentials not configured")
            return False
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=f'Hello {name}, your NAAM verification code is: {code}. Valid for 10 minutes.',
            from_=twilio_number,
            to=mobile
        )
        
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

def is_valid_email(value):
    """Check if value is a valid email"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, value) is not None

def is_valid_mobile(value):
    """Check if value is a valid mobile number"""
    # Accepts formats: +919876543210, 9876543210, +91-9876543210
    mobile_pattern = r'^(\+91[\-\s]?)?[0]?(91)?[6789]\d{9}$'
    return re.match(mobile_pattern, value.replace(' ', '')) is not None

def format_mobile(mobile):
    """Format mobile number to standard format"""
    # Remove spaces and dashes
    mobile = mobile.replace(' ', '').replace('-', '')
    # Add +91 if not present
    if not mobile.startswith('+'):
        if mobile.startswith('91'):
            mobile = '+' + mobile
        else:
            mobile = '+91' + mobile
    return mobile