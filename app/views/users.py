from flask import request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute
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
                last_ins = {"ins_id":user.last_ins, "role_id":user.get_access_id(user.last_ins)[0], "ins_type": Institute.query.get(user.last_ins).ins_type} if user.last_ins else {}
                return APIResponse.success("Signin successful", 200, access_token=access_token, pro_com=user.pro_com, last_ins=last_ins)
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

@app.route('/get_profile', methods=['POST'])
@jwt_required()
def get_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    return APIResponse.success("Success", 200, data=user.user_profile())

@app.route('/switch_ins', methods=['POST'])
@jwt_required()
def switch_ins():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    data = request.get_json()
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    if "ins_id" in data:
        if user.get_access_id(int(data["ins_id"]))[0] != -1:
            user.last_ins = int(data["ins_id"])
            db.session.commit()
            return APIResponse.success("Success", 200)
        else:
            return APIResponse.error("User has no access to this institute", 404)
    else:
        return APIResponse.error("Ins Id not found", 404)

@app.route('/edit_profile', methods=['POST'])
@jwt_required()
def edit_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    data = request.get_json()
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    if user.pro_com == 0:
        mfr = check_data(data, ["pre", "fn", "mn", "ln", "suf", "pn"])
        if mfr: return mfr
        user.pro_com = 1
    for i in ["pre", "fn", "mn", "ln", "suf", "pn"]:
        if i in data:
            setattr(user, i, data[i])
    db.session.commit()
    return APIResponse.success("Profile successfully edited", 200)