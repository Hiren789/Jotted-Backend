from flask_jwt_extended import get_jwt_identity, jwt_required
from functools import wraps
from app.models import User
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
            if 'ins_id' in decoratorargs:
                data = request.get_json()
                if user.get_access_id(data["id"])[0] not in decoratorargs['ins_id']:
                    return APIResponse.error(f"User has no permission to this institute", 403)
                return f(user, data, *args, **kwargs)
            return f(user, *args, **kwargs)
        return decorated_function
    return  decorator