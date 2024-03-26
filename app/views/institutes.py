from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute, UserInstitute, Student
from app.utils import APIResponse, check_data, random_token, profile_image_url, smtp_mail
from app.security import access_control
from sqlalchemy import or_

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
    return APIResponse.success("Success", 200, data=data)

@app.route('/get_institute', methods=['GET'])
@jwt_required()
@access_control()
def get_institute(user):
    data = user.get_institutes()
    ins_id = request.args.get('ins_id')
    for dtaa in data:
        if dtaa['id'] == int(ins_id):
            return APIResponse.success("Success", 200, data=dtaa)
    return APIResponse.error("Institute not found", 404)

@app.route('/get_institute_team_members', methods=['GET'])
@jwt_required()
@access_control()
def get_institute_team_members(user):
    institutes = [x["id"] for x in user.get_institutes()]
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    search_query = request.args.get('search')
    query = db.session.query(User).join(UserInstitute, User.id == UserInstitute.user_id).filter(UserInstitute.ins_id.in_(institutes))
    if search_query:
        search_filter = or_(User.fn.ilike(f"%{search_query}%"), User.ln.ilike(f"%{search_query}%"))
        query = query.filter(search_filter)
    paginated_users = query.distinct(User.id).paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[{"id": x.id, "name": (f"{x.fn} {x.ln}" if x.fn else None), "profile_pic": profile_image_url(x.id)} for x in paginated_users.items],
        pagination={
            'page': paginated_users.page,
            'per_page': paginated_users.per_page,
            'total_pages': paginated_users.pages,
            'total_items': paginated_users.total,
        }
    )

@app.route('/get_team_members', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def get_team_members(user, data):

    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    search_query = request.args.get('search')

    ins_id = data["id"]
    query = db.session.query(User, UserInstitute).join(UserInstitute, User.id == UserInstitute.user_id).filter(UserInstitute.ins_id == ins_id)
    
    if search_query:
        search_filter = or_(User.fn.ilike(f"%{search_query}%"), User.ln.ilike(f"%{search_query}%"))
        query = query.filter(search_filter)
    
    paginated_users = query.paginate(page=page, per_page=per_page)
    
    return APIResponse.success(
        "Success",
        200,
        data=[{"id": x.id, "profile_pic": profile_image_url(x.id), "pre": f"{x.pre}", "name": f"{x.fn} {x.ln}", "suf": f"{x.suf}", "email": f"{x.email}", "pn": f"{x.pn}", "role_id": y.role_id, "students": y.students} for x, y in paginated_users.items],
        pagination={
            'page': paginated_users.page,
            'per_page': paginated_users.per_page,
            'total_pages': paginated_users.pages,
            'total_items': paginated_users.total,
        }
    )

@app.route('/get_team_member', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def get_team_member(user, data):
    ins_id = data["id"]
    member_id = data["member_id"]
    team_member = db.session.query(User, UserInstitute).join(UserInstitute, User.id == UserInstitute.user_id).filter((UserInstitute.ins_id == ins_id) & (User.id == member_id)).first()
    if not team_member:
        return APIResponse.error("Member not found", 400)
    x, y = team_member
    stdss = Institute.query.get(ins_id).get_students(stnds = y.students)
    return APIResponse.success(
        "Success",
        200,
        data={"id": x.id, "profile_pic": profile_image_url(x.id), "pre": f"{x.pre}", "name": f"{x.fn} {x.ln}", "suf": f"{x.suf}", "email": f"{x.email}", "pn": f"{x.pn}", "role_id": y.role_id, "students": stdss}
    )

@app.route('/set_access_team_members', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def set_access_team_members(user, data):
    
    ins_id = data.get('id')
    member_id = data.get('member_id')
    role_id = data.get('role_id')

    uii = UserInstitute.query.filter((UserInstitute.user_id == member_id) & (UserInstitute.ins_id == ins_id)).first()

    if not uii:
        return APIResponse.error("Can not found member within institute", 404)

    if uii.role_id == 0:
        return APIResponse.error("Can not modify the owner", 400)
    
    if (user.get_access_id(ins_id)[0] == 1) and (uii.role_id == 1):
        return APIResponse.error("As a admin you can not modify any Admins", 400)
    
    if (user.get_access_id(ins_id)[0] == 1) and (role_id == 1):
        return APIResponse.error("As a admin you can not make someone Admin", 400)

    if role_id == -1:
        db.session.query(UserInstitute).filter((UserInstitute.user_id == member_id) & (UserInstitute.ins_id == ins_id)).delete()
        db.session.commit()
        return APIResponse.success("Team Member removed", 200)
    else:
        uii.role_id = role_id if role_id else uii.role_id
        if role_id == 2:
            if 'students' not in data:
                APIResponse.error("You need to specify students while setting role as a normal user", 400)
            uii.students = [int(x) for x in data.get('students')]
        else:
            uii.students = []
        db.session.commit()
        return APIResponse.success("Successfully set role and students", 200)

@app.route('/get_institute_students', methods=['GET'])
@jwt_required()
@access_control()
def get_institute_students(user):

    final_stds = []
    insss = user.get_institutes()
    ins_id = request.args.get('ins_id')
    if ins_id:
        insss = [x for x in insss if x["id"] == int(ins_id)]

    for x in insss:
        if x["role_id"] == 2:
            final_stds += user.get_access_id(x["id"])[1]
        else:
            final_stds += [y["id"] for y in Institute.query.get(x["id"]).get_students()]
    final_stds = list(set(final_stds))
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    search_query = request.args.get('search')
    query = Student.query.filter(Student.id.in_(final_stds))
    if search_query:
        search_filter = or_(Student.first_name.ilike(f"%{search_query}%"), Student.middle_name.ilike(f"%{search_query}%"), Student.last_name.ilike(f"%{search_query}%"))
        query = query.filter(search_filter)
    paginated_students = query.distinct(Student.id).paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data={x.id: f"{x.first_name} {x.middle_name} {x.last_name}" for x in paginated_students.items},
        pagination={
            'page': paginated_students.page,
            'per_page': paginated_students.per_page,
            'total_pages': paginated_students.pages,
            'total_items': paginated_students.total,
        }
    )

@app.route('/get_institutes_normal_users', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def get_institutes_normal_users(user, data):
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    search_query = request.args.get('search')
    query = db.session.query(User).join(UserInstitute, User.id == UserInstitute.user_id).filter((UserInstitute.ins_id==data.get("id"))&(UserInstitute.role_id==2))
    if search_query:
        search_filter = or_(User.fn.ilike(f"%{search_query}%"), User.ln.ilike(f"%{search_query}%"))
        query = query.filter(search_filter)
    paginated_users = query.distinct(User.id).paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[{"id": x.id, "name": (f"{x.fn} {x.ln}" if x.fn else None), "profile_pic": profile_image_url(x.id)} for x in paginated_users.items],
        pagination={
            'page': paginated_users.page,
            'per_page': paginated_users.per_page,
            'total_pages': paginated_users.pages,
            'total_items': paginated_users.total,
        }
    )

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

@app.route('/get_campus_by_institute', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1,2])
def get_campus_by_institute(user, data):
    inst = Institute.query.get(data.get("id"))
    return APIResponse.success("Success", 200, data=inst.campus_grade)

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
    usedtmcnt = UserInstitute.query.filter_by(ins_id = data.get('ins_id')).count()
    owneruser = User.query.get(institute.user_id)
    if usedtmcnt >= owneruser.plan[str(institute.ins_type)]["t"]:
        return APIResponse.error(f"Team members limit reached for this institue.", 403)
    if user.get_access_id(data.get("ins_id"))[0] not in [0,1]:
        return APIResponse.error("User has no access to add members to this institute", 403)
    if user.get_access_id(data.get("ins_id"))[0] in [1] and data.get('role_id') in [1, '1']:
        return APIResponse.error("Admin has no access to add admins to this institute", 403)
    token = random_token()
    new_invite = UserInstitute(ins_id = data.get('ins_id'), role_id = data.get('role_id'), token = token, students=[])
    db.session.add(new_invite)
    db.session.commit()
    mail_subject = f'{user.fn} {user.ln} invited you to join {institute.name} on Jotted'
    mail_body = f'Click on following link to join https://jottedonline.com/redeem-token?token={token}'
    smtp_mail(data['email'], mail_subject, mail_body)
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