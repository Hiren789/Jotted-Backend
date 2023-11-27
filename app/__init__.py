from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv(".env")
app.config.update(os.environ)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
db = SQLAlchemy(app)
jwt = JWTManager(app)

from app import views, models
with app.app_context():
    db.create_all()
    db.session.execute(text(f"SET time_zone = '{app.config.get('TIME_ZONE')}'"))
    db.session.commit()