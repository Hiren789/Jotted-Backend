from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app import app, db
from app.models import User, Institute, Student, ArchivedStudent
from app.utils import APIResponse, check_data
from app.security import access_control
from sqlalchemy import or_

@app.route('/add_student', methods=['POST'])
@jwt_required()
def add_student():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    mfr = check_data(data, ['ins_id','campus_id','grade','first_name','middle_name','last_name','suffix','gender','email','phone','zipcode','state','country','city','extra_info','team_member'])
    if mfr: return mfr
    ins = Institute.query.get(data["ins_id"])
    if not ins:
        return APIResponse.error("Institute not found", 400)
    if user.get_access_id(ins.id)[0] not in [0, 1]:
        return APIResponse.error("User has no access to add student to this institute", 403)
    usedcnt = ins.get_students(cnt=True)
    if usedcnt >= ins.get_plan()[str(ins.ins_type)]["s"]:
        return APIResponse.error(f"User's current plan has no capacity to add new student", 400)
    cgexists = ins.cgexists(data["campus_id"], data["grade"])
    if cgexists: return cgexists
    team_memb = data['team_member']
    del data['team_member']
    new_student = Student(**data)
    db.session.add(new_student)
    db.session.commit()
    new_student.set_team_member_acess(team_memb)
    return APIResponse.success("Student added successfully", 201)

@app.route('/get_students', methods=['GET'])
@jwt_required()
def get_students():
    ins_id = request.args.get('ins_id')
    if not ins_id:
        return APIResponse.error("Institute ID is required", 400)
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    access_type, stnds = user.get_access_id(ins_id)
    inst = Institute.query.get(ins_id)
    if not inst:
        return APIResponse.error("Institute not found", 400)    
    if access_type in [0,1]:
        return APIResponse.success("Success", 200, data = inst.get_students(campus_id = request.args.get('campus_id'), grade = request.args.get('grade')))
    elif access_type == 2:
        return APIResponse.success("Success", 200, data = inst.get_students(campus_id = request.args.get('campus_id'), grade = request.args.get('grade'), stnds = stnds))
    else:
        return APIResponse.error("User has no access to this institute", 403)

@app.route('/get_student', methods=['GET'])
@jwt_required()
def get_student():
    std_id = request.args.get('id')
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    stdnt = Student.query.get(std_id)
    if not stdnt:
        return APIResponse.error("Student not found", 400)
    access_type, stnds = user.get_access_id(stdnt.ins_id)
    if (access_type in [0,1]) or (access_type == 2 and int(std_id) in stnds):
        return APIResponse.success("Success", 200, data = stdnt.se_to_json())
    else:
        return APIResponse.error("User has no access to this student", 403)

@app.route('/edit_student', methods=['POST'])
@jwt_required()
def edit_student():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    stnd = Student.query.get(data.get("id"))
    if not stnd:
        return APIResponse.error("Student not found", 400)
    inst = Institute.query.get(stnd.ins_id)
    if user.get_access_id(stnd.ins_id)[0] not in [0, 1]:
        return APIResponse.error("User has no access to add student to this institute", 403)
    if "ins_id" in data:
        return APIResponse.error("Institute ID can not be updated", 400)
    cgexists = inst.cgexists(data["campus_id"] if "campus_id" in data else stnd.campus_id, data["grade"] if "grade" in data else stnd.grade)
    if cgexists: return cgexists
    if "team_member" in data:
        stnd.set_team_member_acess(data['team_member'])
        del data['team_member']
    for k, v in data.items(): setattr(stnd, k, v)    
    db.session.commit()
    return APIResponse.success("Student updated successfully", 201)

@app.route('/remove_student', methods=['DELETE'])
@jwt_required()
def remove_student():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    stnd = Student.query.get(data.get("id"))
    if not stnd:
        return APIResponse.error("Student not found", 400)
    if user.get_access_id(stnd.ins_id)[0] not in [0, 1]:
        return APIResponse.error("User has no access to modify this student", 403)
    stnd.set_team_member_acess([])
    db.session.delete(stnd)
    db.session.commit()
    return APIResponse.success("Student removed successfully", 201)

@app.route('/archive_student', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def archive_student(user, data):
    stnds = Student.query.filter((Student.id.in_(data.get('student_ids'))) & (Student.ins_id == data.get('id'))).all()
    while len(stnds) != 0:
        stnd = stnds.pop()
        archived_student = ArchivedStudent(**{x:y for x,y in stnd.__dict__.items() if x not in ['_sa_instance_state']})
        db.session.add(archived_student)
        db.session.delete(stnd)
    db.session.commit()
    return APIResponse.success("Student Archived successfully", 201)

@app.route('/unarchive_student', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def unarchive_student(user, data):
    stnds = ArchivedStudent.query.filter((ArchivedStudent.id.in_(data.get('student_ids'))) & (ArchivedStudent.ins_id == data.get('id'))).all()
    while len(stnds) != 0:
        stnd = stnds.pop()
        archived_student = Student(**{x:y for x,y in stnd.__dict__.items() if x not in ['_sa_instance_state']})
        db.session.add(archived_student)
        db.session.delete(stnd)
    db.session.commit()
    return APIResponse.success("Student Archived successfully", 201)

@app.route('/get_archive_student', methods=['POST'])
@jwt_required()
@access_control(ins_id=[0,1])
def get_archive_student(user, data):

    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    sort_by = request.args.get('sort_by', default='id', type=str)
    sort_order = request.args.get('sort_order', default='asc', type=str)
    search_query = request.args.get('search')

    if sort_order not in ['asc', 'desc']:
        return APIResponse.error("Invalid sort order", 400)

    query = ArchivedStudent.query.filter(ArchivedStudent.ins_id == data.get('id'))
    
    if search_query:
        search_filter = or_(ArchivedStudent.first_name.ilike(f"%{search_query}%"), ArchivedStudent.middle_name.ilike(f"%{search_query}%"), ArchivedStudent.last_name.ilike(f"%{search_query}%"))
        query = query.filter(search_filter)

    if hasattr(ArchivedStudent, sort_by):
        column = getattr(ArchivedStudent, sort_by)
        query = query.order_by(column.asc() if sort_order == 'asc' else column.desc())
    else:
        return APIResponse.error("Invalid sort column", 400)
    
    paginated_todos = query.paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[x.se_to_json() for x in paginated_todos.items],
        pagination={
            'page': paginated_todos.page,
            'per_page': paginated_todos.per_page,
            'total_pages': paginated_todos.pages,
            'total_items': paginated_todos.total,
        }
    )