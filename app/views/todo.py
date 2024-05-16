from flask import request
from flask_jwt_extended import jwt_required
from app import app, db
from sqlalchemy import func
from app.models import Todo, list_to_members, list_to_students
from app.utils import APIResponse, check_data
from app.security import access_control
from datetime import datetime

@app.route('/add_todo', methods=['POST'])
@jwt_required()
@access_control(check_data=['title','body','priority','status','students','read_members','edit_members'])
def create_todo(user):
    data = request.get_json()
    if user.id not in data['edit_members']:
        data['edit_members'].append(user.id)
    if user.id in data['read_members']:
        data['read_members'].remove(user.id)
    todo = Todo(**data)
    db.session.add(todo)
    db.session.commit()
    return APIResponse.success("To-Do item created", 201)

@app.route('/get_todos', methods=['GET'])
@jwt_required()
@access_control()
def get_todos(user):

    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    sort_by = request.args.get('sort_by', default='due', type=str)
    sort_order = request.args.get('sort_order', default='asc', type=str)
    search_query = request.args.get('search')
    
    if sort_order not in ['asc', 'desc']:
        return APIResponse.error("Invalid sort order", 400)

    query = Todo.query.filter((func.json_contains(Todo.read_members, str(user.id))) | (func.json_contains(Todo.edit_members, str(user.id))))

    student_id = request.args.get('student_id')
    if student_id:
        query = query.filter(func.json_contains(Todo.students, str(student_id)))

    if search_query:
        query = query.filter(Todo.title.ilike(f"%{search_query}%"))
    
    if hasattr(Todo, sort_by):
        column = getattr(Todo, sort_by)
        query = query.order_by(column.asc() if sort_order == 'asc' else column.desc())
    else:
        return APIResponse.error("Invalid sort column", 400)
    
    paginated_todos = query.paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[{**todo.td_to_json(), "access_type": 1 if user.id in todo.edit_members else 0} for todo in paginated_todos.items],
        pagination={
            'page': paginated_todos.page,
            'per_page': paginated_todos.per_page,
            'total_pages': paginated_todos.pages,
            'total_items': paginated_todos.total,
        }
    )

@app.route('/get_due_todos', methods=['GET'])
@jwt_required()
@access_control()
def get_due_todos(user):

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return APIResponse.error("Both start_date and end_date parameters are required.", 404)

    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return APIResponse.error("Invalid date format. Please provide dates in YYYY-MM-DD format.", 403)

    todos = Todo.query.filter((func.json_contains(Todo.read_members, str(user.id))) | (func.json_contains(Todo.edit_members, str(user.id)))).filter(Todo.due.between(start_date, end_date)).all()
    
    return APIResponse.success(
        "Success",
        200,
        data=[{**todo.td_to_json(), "access_type": 1 if user.id in todo.edit_members else 0} for todo in todos]
    )

@app.route('/edit_todo', methods=['POST'])
@jwt_required()
@access_control(todo="")
def edit_todo(user, data, todo):
    mfr = check_data(data, ['id'])
    if mfr: return mfr
    if 'edit_members' in data and data['edit_members'] == []:
        return APIResponse.error("To Do item must have one assignee", 404)
    for key, value in data.items():
        setattr(todo, key, value)
    db.session.commit()
    return APIResponse.success("To-Do Updated Successfully", 200)

@app.route('/get_todo', methods=['POST'])
@jwt_required()
@access_control()
def get_todo(user, data, todo):
    tmpp = todo.td_to_json()
    if user.id not in tmpp["read_members"]+tmpp["edit_members"]:
        return APIResponse.error("User has no access to this todo", 403)
    tmpp["read_members"] = list_to_members(tmpp["read_members"])
    tmpp["edit_members"] = list_to_members(tmpp["edit_members"])
    tmpp["students"] = list_to_students(tmpp["students"])
    data = {**tmpp, "access_type": 1 if user.id in todo.edit_members else 0}
    return APIResponse.success("Success", 200, data=data)

@app.route('/remove_todo', methods=['DELETE'])
@jwt_required()
@access_control(todo="")
def remove_todo(user, data, todo):
    db.session.delete(todo)
    db.session.commit()
    return APIResponse.success("To-Do Deleted Successfully", 200)