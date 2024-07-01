from flask import request, redirect, session
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute
from app.utils import APIResponse, check_data, resizer, profile_image_url, random_token, smtp_mail, urlonpath
import requests

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    # mfr = check_data(data, ['pre', 'fn', 'mn', 'ln', 'suf', 'email', 'pw'])
    mfr = check_data(data, ['email', 'pw'])
    if mfr: return mfr
    user = User.query.filter(User.email == data.get('email')).first()
    if user:
        return APIResponse.error("This Email is associated with an Existing Account", 409)
    if data.get('pn'):
        user = User.query.filter(User.pn == data.get('pn')).first()
        if user:
            return APIResponse.error("This Phone Number is associated with an Existing Account", 409)
    new_user = User(**data)
    new_user.set_password(data.get('pw'))
    db.session.add(new_user)
    db.session.commit()
    access_token = create_access_token(identity=new_user.id)
    return APIResponse.success("Signup successfull", 200, access_token=access_token)

@app.route('/forget_password', methods=['POST'])
def forget_password():
    data = request.get_json()
    if data.get('email'):
        user = User.query.filter(User.email == data.get('email')).first()
        if not user:
            return APIResponse.error("User not found with this associated email id", 409)
    elif data.get('pn'):
        user = User.query.filter(User.pn == data.get('pn')).first()
        if not user:
            return APIResponse.error("User not found with this associated Phone Number", 409)
    else:
        return APIResponse.error("Email or Phone Number is required to forget password", 400)
    new_password = random_token(24)
    user.set_password(new_password)
    db.session.commit()
    smtp_mail(user.email, "Jotted password reset", f"Your new password is {new_password}")
    return APIResponse.success("Success! Please check your email for additional instructions.", 200)

@app.route('/reset_password', methods=['POST'])
@jwt_required()
def reset_password():
    current_user = get_jwt_identity()
    data = request.get_json()
    pw = data.get('pw')
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    if pw == "":
        return APIResponse.error("Can not set blank password", 403)
    if len(pw) < 8:
        return APIResponse.error("Password must be at least 8 characters long ", 403)
    user.set_password(pw)
    db.session.commit()
    return APIResponse.success("Password updated successfully", 200)

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
            if user.pw and user.check_password(str(pw)):
                access_token = create_access_token(identity=user.id)
                last_ins = {"ins_id":user.last_ins, "role_id":user.get_access_id(user.last_ins)[0], "ins_type": Institute.query.get(user.last_ins).ins_type} if user.last_ins and Institute.query.get(user.last_ins) else {}
                return APIResponse.success("Signin successful", 200, access_token=access_token, pro_com=user.pro_com, last_ins=last_ins)
            else:
                return APIResponse.error("Email or Password is incorrect", 400)
    else:
        return APIResponse.error("Email and Password are required", 400)

@app.route('/google_login')
def google_login():
    auth_url = (
        f'{app.config.get("AUTH_URI")}?client_id={app.config.get("CLIENT_ID")}&redirect_uri={app.config.get("REDIRECT_URI")}&'
        'response_type=code&scope=email'
    )
    return redirect(auth_url)

@app.route('/auth/google/callback')
def auth_callback():
    auth_code = request.args.get('code')
    token_data = {
        'code': auth_code,
        'client_id': app.config.get("CLIENT_ID"),
        'client_secret': app.config.get("CLIENT_SECRET"),
        'redirect_uri': app.config.get("REDIRECT_URI"),
        'grant_type': 'authorization_code'
    }
    token_response = requests.post(app.config.get("TOKEN_URI"), data=token_data)
    token_info = token_response.json()
    if 'access_token' not in token_info:
        return 'Authentication failed'
    session['access_token'] = token_info['access_token']
    user_info_response = requests.get(
        app.config.get("USER_INFO_URI"),
        headers={'Authorization': f'Bearer {token_info["access_token"]}'}
    )
    user_info = user_info_response.json()
    if "email" not in user_info:
        return APIResponse.error("Email id not found in Google Account", 404)
    user = User.query.filter_by(email=user_info["email"]).first()
    if not user:
        data = {"email": user_info["email"]}
        if "name" in user_info:
            nmmmm = user_info["name"].split(" ")
            data["fn"] = nmmmm[0]
            data["ln"] = " ".join(nmmmm[1:])
        user = User(**data)
        db.session.add(user)
        db.session.commit()
        access_token = create_access_token(identity=user.id)
        session.pop('access_token', None)
        if "picture" in user_info:
            file_path = f"{app.config['UPLOAD_FOLDER']}/{user.id}.jpeg"
            urlonpath(user_info["picture"].replace('s96', f"s{app.config['PROFILE_PIC_SIZE']}"), file_path)
        return APIResponse.success("Signup successfull", 200, access_token=access_token)
    else:
        access_token = create_access_token(identity=user.id)
        session.pop('access_token', None)
        return redirect(f"https://jottedonline.com/google-callback-url?token={access_token}")

@app.route('/get_profile', methods=['POST'])
@jwt_required()
def get_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("Couldn't find a user account", 400)
    data = user.user_profile()
    insss = Institute.query.get(user.last_ins)
    data["last_ins"] = {"ins_id":insss.id, "name":insss.name, "role_id":user.get_access_id(insss.id)[0], "ins_type": insss.ins_type} if insss else {}
    data["pro_com"] = user.pro_com
    return APIResponse.success("Success", 200, data=data)

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
    if "pn" in data and User.query.filter_by(pn = data["pn"]).first():
        return APIResponse.error("Phone number is already in use", 400)
    if user.pro_com == 0:
        mfr = check_data(data, ["pre", "fn", "mn", "ln", "suf", "pn", "gender"])
        if mfr: return mfr
        user.pro_com = 1
    for i in ["pre", "fn", "mn", "ln", "suf", "pn", "gender"]:
        if i in data:
            setattr(user, i, data[i])
    db.session.commit()
    return APIResponse.success("Profile successfully edited", 200)

@app.route('/edit_profile_picture', methods=['POST'])
@jwt_required()
def edit_profile_picture():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file.filename.split(".")[-1] not in app.config["ALLOWED_EXTENSIONS"]:
            return APIResponse.error("This format is not allowed", 406)
        file_path = f"{app.config['UPLOAD_FOLDER']}/{user.id}.jpeg"
        file.save(file_path)
        resizer(file_path, app.config['PROFILE_PIC_SIZE'])
        return APIResponse.success("Profile Picture successfully edited", 200, image_url = profile_image_url(user.id))
    else:
        return APIResponse.success("Profile Picture not found", 404)