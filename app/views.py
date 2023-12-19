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

@app.route('/get_price_plan', methods=['POST'])
def get_price_plan():
    data = request.get_json()
    it = int(data.get('it'))
    s = int(data.get('s'))
    t = int(data.get('t'))
    d = data.get('d')
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
    return APIResponse.success("Success", 200, data=data)