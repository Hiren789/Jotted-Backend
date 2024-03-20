from flask import request
from flask_jwt_extended import jwt_required
from app import app, db
from sqlalchemy import func
from app.models import Goals, list_to_members, list_to_students
from app.utils import APIResponse, check_data
from app.security import access_control

@app.route('/add_goal', methods=['POST'])
@jwt_required()
@access_control(check_data=['title','student_id','description','objectives','percent'])
def add_goal(user):
    data = request.get_json()
    goal = Goals(**data)
    db.session.add(goal)
    db.session.commit()
    goal.log_percent(data['percent'])
    db.session.commit()
    return APIResponse.success("Goal item created", 201)

@app.route('/get_goals', methods=['GET'])
@jwt_required()
@access_control()
def get_goals(user):

    student_id = request.args.get('student_id')
    if not student_id:
        return APIResponse.error("Student ID is required", 403)

    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    sort_by = request.args.get('sort_by', default='id', type=str)
    sort_order = request.args.get('sort_order', default='asc', type=str)
    search_query = request.args.get('search')
    
    if sort_order not in ['asc', 'desc']:
        return APIResponse.error("Invalid sort order", 400)

    query = Goals.query.filter_by(student_id = student_id)

    if search_query:
        query = query.filter(Goals.title.ilike(f"%{search_query}%"))
    
    if hasattr(Goals, sort_by):
        column = getattr(Goals, sort_by)
        query = query.order_by(column.asc() if sort_order == 'asc' else column.desc())
    else:
        return APIResponse.error("Invalid sort column", 400)
    
    paginated_goals = query.paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[{**goal.ga_to_json(), "logs": goal.history()} for goal in paginated_goals.items],
        pagination={
            'page': paginated_goals.page,
            'per_page': paginated_goals.per_page,
            'total_pages': paginated_goals.pages,
            'total_items': paginated_goals.total,
        }
    )

@app.route('/edit_goal', methods=['POST'])
@jwt_required()
@access_control(goal="")
def edit_goal(user, data, goal):
    mfr = check_data(data, ['id'])
    if mfr: return mfr
    for k in ["student_id", "percent"]:
        if k in data:
            APIResponse.error("Goal Student_id or percent can not be updated", 403)
    for key, value in data.items():
        setattr(goal, key, value)
    db.session.commit()
    return APIResponse.success("Goal Updated Successfully", 200)

@app.route('/get_goal', methods=['POST'])
@jwt_required()
@access_control(goal="")
def get_goal(user, data, goal):
    data = {**goal.ga_to_json(), "logs": goal.history()}
    return APIResponse.success("Success", 200, data=data)

@app.route('/goal_log_percent', methods=['POST'])
@jwt_required()
@access_control(goal="")
def goal_log_percent(user, data, goal):
    mfr = check_data(data, ['id', 'percent'])
    if mfr: return mfr
    goal.log_percent(data["percent"])
    db.session.commit()
    return APIResponse.success("Goal Log Created", 200)

@app.route('/remove_goal', methods=['DELETE'])
@jwt_required()
@access_control(goal="")
def remove_goal(user, data, goal):
    goal.clear_logs()
    db.session.delete(goal)
    db.session.commit()
    return APIResponse.success("Goal Deleted Successfully", 200)