from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute, UserInstitute, Student
from app.utils import APIResponse, check_data, random_token
from app.security import access_control

@app.route('/add_institute', methods=['POST'])
@jwt_required()
def add_institute():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    mfr = check_data(data, ['name', 'campus_type', 'address', 'district', 'state', 'country', 'zipcode', "ins_type", "campus_grade"])
    if mfr: return mfr
    usedcnt = user.get_institutes(cnt=True, role_id="0")
    if usedcnt >= user.plan[str(data.get("ins_type"))]["c"]:
        return APIResponse.error(f"User's current plan has no capacity to add new institute", 400)
    new_institute = Institute(user_id=user.id, **data)
    db.session.add(new_institute)
    db.session.commit()
    new_user_institute = UserInstitute(user_id=user.id, ins_id=new_institute.id, role_id=0, students=[])
    db.session.add(new_user_institute)
    db.session.commit()
    return APIResponse.success("Institute added successfully", 201)

@app.route('/get_institutes', methods=['GET'])
@jwt_required()
@access_control()
def get_institutes(user):
    data = user.get_institutes()
    return APIResponse.success("Success", 201, data=data)

@app.route('/get_institutes_normal_users', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def get_institutes_normal_users(user, data):
    usrids = [x.user_id for x in db.session.query(UserInstitute).filter((UserInstitute.ins_id==data.get("id"))&(UserInstitute.role_id==2)).all()]
    usrs = {x.id:(f"{x.fn} {x.ln}" if x.fn else None) for x in db.session.query(User).filter((User.id.in_(usrids))).all()}
    return APIResponse.success("Success", 201, data=usrs)

@app.route('/edit_institute', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def edit_institute(user, data):
    inst = Institute.query.get(data.get("id"))
    if "user_id" in data:
        return APIResponse.error("User ID can not be updated", 400)
    if "campus_grade" in data:
        chk = inst.verify_campus_grades(data["campus_grade"])
        if chk: return chk
    for k, v in data.items():
        setattr(inst, k, v)
    db.session.commit()
    return APIResponse.success("Institute updated successfully", 201)

@app.route('/remove_institute', methods=['DELETE'])
@jwt_required()
@access_control(ins_id=[0])
def remove_institute(user, data):
    db.session.query(UserInstitute).filter_by(ins_id=data.get("id")).delete()
    db.session.query(Student).filter_by(ins_id=data.get("id")).delete()
    inst = Institute.query.get(data.get("id"))
    db.session.delete(inst)
    db.session.commit()
    return APIResponse.success("Institute removed successfully", 201)

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
    if user.get_access_id(data.get("ins_id"))[0] not in [0,1]:
        return APIResponse.error("User has no access to add members to this institute", 403)
    token = random_token()
    new_invite = UserInstitute(ins_id = data.get('ins_id'), role_id = data.get('role_id'), token = token, students=[])
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