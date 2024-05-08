from flask import jsonify
import secrets
import os
from PIL import Image, ImageOps
from app import app
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from io import BytesIO

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

def smtp_mail(recipient, subject, body, body_type="plain"):
    sender = app.config['SMTP_MAIL']
    password = app.config['SMTP_PW']

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    msg.attach(MIMEText(body, body_type))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipient, msg.as_string())

def random_token(length=16):
    token = secrets.token_hex(length // 2)
    return token

def profile_image_url(user_id):
    return f'''{app.config['BACKEND_URL']}/static/profile_pic/{user_id}.jpeg?v={int(os.path.getmtime(f"{app.config['UPLOAD_FOLDER']}/{user_id}.jpeg"))}''' if os.path.exists(f"{app.config['UPLOAD_FOLDER']}/{user_id}.jpeg") else None

def student_profile_image_url(student_id):
    return f'''{app.config['BACKEND_URL']}/static/student_profile_pic/{student_id}.jpeg?v={int(os.path.getmtime(f"{app.config['STUDENT_UPLOAD_FOLDER']}/{student_id}.jpeg"))}''' if os.path.exists(f"{app.config['STUDENT_UPLOAD_FOLDER']}/{student_id}.jpeg") else None

def resizer(file_path, resize_size):
    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    ImageOps.fit(img, (int(resize_size), int(resize_size))).save(file_path)

def urlonpath(url, file_path):
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    image.save(file_path, 'JPEG')

def calculate_price(it, s, t, d):
    pricing = {0: {"s": {10: 0, 30: 5, 150: 10, 10000000: 25}},
           1: {"s": {30: 15, 50: 25, 100: 40, 250: 75, 500: 150, 1000: 300, 1500: 450, 2000: 600, 2500: 750, 3000: 1000, 3500: 1250, 4000: 1500, 4500: 1750, 5000: 2000, 6000: 2700, 7000: 3400, 8000: 4100, 9000: 4800, 10000: 5500, 12500: 7250, 15000: 9000, 10000000: 12500},
               "sf": {30: 5, 50: 5, 100: 8, 250: 10, 500: 15, 1000: 25, 1500: 25, 2000: 25, 2500: 30, 3000: 30, 3500: 30, 4000: 30, 4500: 30, 5000: 50, 6000: 50, 7000: 50, 8000: 75, 9000: 75, 10000: 100, 12500: 125, 15000: 150, 10000000: 150},
               "sa": {5: 5, 8: 5, 10: 5, 15: 5, 25: 5, 30: 5, 50: 7.50, 75: 7.50, 100: 10, 125: 10, 150: 10, 10000000:0}}}

    discounts = {0: {"m": 1, "1y": 10/12},
                1: {"m": 1, "1y": 0.9, "2y": 0.85, "3y": 0.8},
                2: {"m": 1, "1y": 12, "2y": 24, "3y": 36}}
    if it not in pricing:
        return "Invalid institute type"
    if s not in pricing[it]["s"]:
        return "Invalid Students count"
    if d not in discounts[it]:
        return "Invalid Duration"
    k = discounts[it][d]
    price = pricing[it]["s"][s]
    if it == 1:
        if t not in pricing[it]["sa"]:
            return "Invalid Team Member Count"
        if pricing[it]["sf"][s] <= t:
            price += 1000 if t == 10000000 else (
                t-pricing[it]["sf"][s])*pricing[it]["sa"][pricing[it]["sf"][s]]
    price *= discounts[2][d]
    data = {"origional_price":int(price), "discounted_price":int(price*k), "price_per_month_per_student":round(price*k/(discounts[2][d]*s), 2), "price_per_year_per_student":round(price*k*12/(discounts[2][d]*s), 2)}
    return data