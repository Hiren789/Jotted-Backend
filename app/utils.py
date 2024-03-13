from flask import jsonify
import secrets
import os
from PIL import Image, ImageOps
from app import app

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

def random_token(length=16):
    token = secrets.token_hex(length // 2)
    return token

def profile_image_url(user_id):
    return f"{app.config['BACKEND_URL']}/static/profile_pic/{user_id}.jpeg" if os.path.exists(f"{app.config['UPLOAD_FOLDER']}/{user_id}.jpeg") else None

def resizer(file_path, resize_size):
    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)
    ImageOps.fit(img, (int(resize_size), int(resize_size))).save(file_path)