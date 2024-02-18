from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app import app, db
from app.models import User
from app.utils import APIResponse, check_data

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    # mfr = check_data(data, ['pre', 'fn', 'mn', 'ln', 'suf', 'email', 'pw'])
    mfr = check_data(data, ['email', 'pw'])
    if mfr: return mfr
    user = User.query.filter(User.email == data.get('email')).first()
    if user:
        return APIResponse.error("This Email is associated with an Existing Account", 409)
    else:
        new_user = User(**data)
        new_user.set_password(data.get('pw'))
        db.session.add(new_user)
        db.session.commit()
        return APIResponse.success("Signup successfull", 200)

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    email = data.get('email')
    pw = data.get('pw')
    if email and pw:
        user = User.query.filter_by(email=email).first()
        if not user:
            return APIResponse.error("Couldn't find a account with given email", 400)
        else:
            if user.check_password(pw):
                access_token = create_access_token(identity=user.id)
                return APIResponse.success("Signin successful", 200, access_token=access_token, pro_com=user.pro_com)
            else:
                return APIResponse.error("Email or Password is incorrect", 400)
    else:
        return APIResponse.error("Email and Password are required", 400)

@app.route('/set_payment', methods=['POST'])
@jwt_required()
def set_payment():
    current_user = get_jwt_identity()
    data = request.get_json()
    plan = data.get('plan')
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    if plan:
        user.plan = plan
        db.session.commit()
        return APIResponse.success("Plan updated successfully", 200)
    else:
        return APIResponse.error("Plan is required", 400)