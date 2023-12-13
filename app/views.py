from flask import request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute, UserInstitute
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

def check_data(data, required_fields):
    for chk in required_fields:
        if chk not in data:
            return APIResponse.error(f"{chk.title()} is required", 400)
    return None

@app.route('/')
def hello():
    print(User.query.get(1).get_access_id(4))
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
        new_user = User(**data)
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
    
# Set Payment Plan
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
    mfr = check_data(data, ['name', 'campus_type', 'address', 'district', 'state', 'country', 'zipcode', "ins_type"])
    if mfr: return mfr
    usedcnt = user.get_institutes(cnt=True, role_id=0)
    if usedcnt >= user.plan[str(data.get("ins_type"))]["c"]:
        return APIResponse.error(f"User's current plan has no capacity to add new institute", 400)
    new_institute = Institute(user_id=user.id, **data)
    db.session.add(new_institute)
    db.session.commit()
    new_user_institute = UserInstitute(user_id=user.id, ins_id=new_institute.id, role_id=0)
    db.session.add(new_user_institute)
    db.session.commit()
    return APIResponse.success("Institute added successfully", 201)

@app.route('/get_institutes', methods=['GET'])
@jwt_required()
def get_institutes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    data = user.get_institutes()
    return APIResponse.success("Success", 201, data=data)

@app.route('/edit_institute', methods=['POST'])
@jwt_required()
def edit_institute():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    if user.get_access_id(data.get("id")) not in [0,1]:
        return APIResponse.error("User has no access to modify this institute", 403)    
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
    if user.get_access_id(data.get("id")) != 0:
        return APIResponse.error("User has no access to remove this institute", 403)
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
    mfr = check_data(data, ['ins_id', 'email', 'role_id'])
    if mfr: return mfr    
    if data.get('role_id') not in [1,2,'1','2']:
        return APIResponse.error("Invalid value for Role ID", 403)
    institute = Institute.query.get(data.get('ins_id'))
    if not institute:
        return APIResponse.error("Institute not found", 400)
    if user.get_access_id(data.get("ins_id")) not in [0,1]:
        return APIResponse.error("User has no access to add members to this institute", 403)
    token = random_token()
    new_invite = UserInstitute(ins_id = data.get('ins_id'), role_id = data.get('role_id'), token = token)
    db.session.add(new_invite)
    db.session.commit()
    # SEND INVITE THORUGH EMAIL WITH INVITE CODE
    return APIResponse.success("Sent invite successfully", 201, invite_code=token)

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
    existingrel = UserInstitute.query.filter(UserInstitute.user_id == user.id, UserInstitute.ins_id == reqq.ins_id).first()
    if existingrel:
        if reqq.role_id < existingrel.role_id:
            db.session.delete(reqq)
            existingrel.role_id = reqq.role_id            
            db.session.commit()
            return APIResponse.success("Account Upgraded successfully", 201)
        else:
            return APIResponse.error("You are already a team member of this institute", 409)
    else:
        reqq.user_id = user.id
        reqq.token = None
        db.session.commit()
        return APIResponse.success("Request Accepted successfully", 201)