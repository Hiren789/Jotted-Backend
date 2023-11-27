from flask import request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute, UserInstitute, Plans
import secrets

# RESPONSE CLASS
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


@app.route('/')
def hello():
    return 'Hello, World!'

# Signup API
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    mfr = check_data(data, ['pre', 'fn', 'mn', 'ln', 'suf', 'email', 'pw'])
    if mfr: return mfr
    user = User.query.filter((User.email == data.get('email')) | (User.pn == data.get('pn'))).first()
    if user:
        return APIResponse.error("This Email or Phone Number is associated with an Existing Account", 409)
    else:
        new_user = User(**data, plan=1)
        new_user.set_password(data.get('pw'))
        db.session.add(new_user)
        db.session.commit()
        return APIResponse.success("Signup successfull", 200)

# Signin
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
                return APIResponse.success("Signin successful", 200, access_token=access_token)
            else:
                return APIResponse.error("Email or Password is incorrect", 400)
    else:
        return APIResponse.error("Email and Password are required", 400)

def check_data(data, required_fields):
    for chk in required_fields:
        if chk not in data:
            return APIResponse.error(f"{chk.title()} is required", 400)
    return None

def check_plan_perm(user, data):
    plan = user.plan
    if not plan:
        return APIResponse.error(f"User has no active plan", 400)
    if "add" in data:
        if data.get("add") == "institute":
            user_plan = Plans.query.get(user.plan)
            already_used = len(Institute.query.filter_by(user_id = user.id).all())
            if already_used >= user_plan.perm.get("institute"):
                return APIResponse.error(f"User's current plan has no capacity to add new institute", 400)
    if "institute" in data:
        chk_perm = data.get("institute")
        institute = Institute.query.get(chk_perm.get('id'))
        if not institute:
            return APIResponse.error("Institute not found for given id", 400)
        if institute.user_id != user.id:
            userinst = UserInstitute.query.filter((UserInstitute.user_id == user.id) & (UserInstitute.ins_id == chk_perm.get('id'))).first()
            if not userinst:
                return APIResponse.error(f"User has no access to given institute", 400)
            if chk_perm.get("role") == 1:
                if userinst.role != 1:
                    return APIResponse.error(f"User has no admin access to given institute", 400)
    return None

def random_token(length=16):
    token = secrets.token_hex(length // 2)
    return token

# Institutes
@app.route('/add_institute', methods=['POST'])
@jwt_required()
def add_institute():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    cup = check_plan_perm(user, {"add":"institute"})
    if cup: return cup
    mfr = check_data(data, ['name', 'campus_type', 'address', 'district', 'state', 'country', 'zipcode'])
    if mfr: return mfr
    new_institute = Institute(user_id=current_user, **data)
    db.session.add(new_institute)
    db.session.commit()
    return APIResponse.success("Institute added successfully", 201)

@app.route('/get_institutes', methods=['GET'])
@jwt_required()
def get_institutes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    insss = Institute.query.filter_by(user_id = user.id).all()
    data = [x.ie_to_json() for x in insss]
    return APIResponse.success("Success", 201, data=data)

@app.route('/edit_institute', methods=['POST'])
@jwt_required()
def edit_institute():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    cup = check_plan_perm(user, {"institute":{"id":data.get("id"), "role": 1}})
    if cup: return cup
    inst = Institute.query.get(data.get("id"))
    if "user_id" in data:
        return APIResponse.error("User ID can not be updated", 400)
    for k, v in data.items():
        setattr(inst, k, v)
    db.session.commit()
    return APIResponse.success("Institute updated successfully", 201)

@app.route('/remove_institute', methods=['DELETE'])
@jwt_required()
def remove_institute():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    cup = check_plan_perm(user, {"institute":{"id":data.get("id"), "role": 1}})
    if cup: return cup
    db.session.query(UserInstitute).filter_by(ins_id=data.get("id")).delete()
    inst = Institute.query.get(data.get("id"))
    db.session.delete(inst)
    db.session.commit()
    return APIResponse.success("Institute removed successfully", 201)

# Institutes
@app.route('/send_institute_invite', methods=['POST'])
@jwt_required()
def send_institute_invite():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    mfr = check_data(data, ['ins_id', 'email', 'role'])
    if mfr: return mfr    
    institute = Institute.query.get(data.get('ins_id'))
    if not institute:
        return APIResponse.error("Institute not found", 400)
    cup = check_plan_perm(user, {"institute":{"id":data.get("ins_id"), "role": 1}})
    if cup: return cup
    token = random_token()
    new_invite = UserInstitute(ins_id = data.get('ins_id'), role = data.get('role'), token = token)
    db.session.add(new_invite)
    db.session.commit()
    # SEND INVITE THORUGH EMAIL WITH INVITE CODE
    return APIResponse.success("Sent invite successfully", 201)

@app.route('/accept_institute_invite', methods=['POST'])
@jwt_required()
def accept_institute_invite():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    mfr = check_data(data, ['token'])
    if mfr: return mfr
    reqq = UserInstitute.query.filter_by(token = data.get('token')).first()
    if not reqq:
        return APIResponse.error("Invitation Not found", 400)
    reqq.user_id = user.id
    reqq.token = None
    db.session.commit()
    return APIResponse.success("Request Accepted successfully", 201)