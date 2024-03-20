from flask import jsonify
import secrets
import os
from PIL import Image, ImageOps
from app import app
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class APIResponse:
    @staticmethod
    def success(message, status_code, **kwargs):
        response = {
            "message": message,
            "status_code": status_code,
            **kwargs
        }
        return jsonify(response), status_code

    @staticmethod
    def error(message, status_code, **kwargs):
        response = {
            "error": message,
            "status_code": status_code,
            **kwargs
        }
        return jsonify(response), status_code
    
def check_data(data, required_fields):
    for chk in required_fields:
        if chk not in data:
            return APIResponse.error(f"{chk.title()} is required", 400)
    return None

def smtp_mail(recipient, subject, body):
    sender = app.config['SMTP_MAIL']
    password = app.config['SMTP_PW']

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipient, msg.as_string())

def random_token(length=16):
    token = secrets.token_hex(length // 2)
    return token

def profile_image_url(user_id):
    return f"{app.config['BACKEND_URL']}/static/profile_pic/{user_id}.jpeg" if os.path.exists(f"{app.config['UPLOAD_FOLDER']}/{user_id}.jpeg") else None

def student_profile_image_url(student_id):
    return f"{app.config['BACKEND_URL']}/static/student_profile_pic/{student_id}.jpeg" if os.path.exists(f"{app.config['STUDENT_UPLOAD_FOLDER']}/{student_id}.jpeg") else None

def resizer(file_path, resize_size):
    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    ImageOps.fit(img, (int(resize_size), int(resize_size))).save(file_path)