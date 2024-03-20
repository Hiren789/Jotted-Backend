from flask_jwt_extended import get_jwt_identity, jwt_required
from functools import wraps
from app.models import User, Todo, Notes, Goals, Student
from app.utils import APIResponse
from flask import request

def access_control(**decoratorargs):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            current_user = get_jwt_identity()
            user = User.query.get(current_user)
            if not user:
                return APIResponse.error("User not found", 404)
            
            if 'check_form_data' in decoratorargs:
                data = request.form
                for chk in decoratorargs['check_form_data']:
                    if chk not in data:
                        return APIResponse.error(f"{chk.title()} is required", 400)
            if 'note' in decoratorargs:
                data = request.form
                note = Notes.query.get(data["id"])
                if not note:
                    return APIResponse.error("Note does not exists", 404)
                if user.id not in note.edit_members:
                    return APIResponse.error("User has no access to modify this Note", 404)
                return f(user, data, note, *args, **kwargs)

            if 'check_data' in decoratorargs:
                data = request.get_json()
                for chk in decoratorargs['check_data']:
                    if chk not in data:
                        return APIResponse.error(f"{chk.title()} is required", 400)
            if 'ins_id' in decoratorargs:
                data = request.get_json()
                if user.get_access_id(data["id"])[0] not in decoratorargs['ins_id']:
                    return APIResponse.error(f"User has no permission to this institute", 403)
                return f(user, data, *args, **kwargs)
            if 'todo' in decoratorargs:
                data = request.get_json()
                todo = Todo.query.get(data["id"])
                if not todo:
                    return APIResponse.error("To-Do does not exists", 404)
                if user.id not in todo.edit_members:
                    return APIResponse.error("User has no access to modify this To-Do", 404)
                return f(user, data, todo, *args, **kwargs)
            if 'goal' in decoratorargs:
                data = request.get_json()
                goal = Goals.query.get(data["id"])
                if not goal:
                    return APIResponse.error("Goal does not exists", 404)
                stnd = Student.query.get(goal.student_id)
                if user.get_access_id(stnd.ins_id)[0] not in [0,1,2]:
                    return APIResponse.error("User has no access to this Goal", 404)
                return f(user, data, goal, *args, **kwargs)
            return f(user, *args, **kwargs)
        return decorated_function
    return  decorator