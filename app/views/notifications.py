from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import app, db
from app.models import User, Notifications
from app.utils import APIResponse, check_data

@app.route('/get_notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    
    query = Notifications.query.filter_by(user_id = current_user).order_by(Notifications.id.desc())
    
    paginated_notes = query.paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[_.ne_to_json() for _ in paginated_notes.items],
        pagination={
            'page': paginated_notes.page,
            'per_page': paginated_notes.per_page,
            'total_pages': paginated_notes.pages,
            'total_items': paginated_notes.total,
        }
    )

@app.route('/add_test_notification', methods=['POST'])
@jwt_required()
def add_test_notification():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    mfr = check_data(data, ['title','body'])
    if mfr: return mfr
    nt = Notifications(user_id = current_user, title = data["title"], body = data["body"])
    db.session.add(nt)
    db.session.commit()
    return APIResponse.success("Notification Created", 201)

@app.route('/read_notifications', methods=['POST'])
@jwt_required()
def read_notifications():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    data = request.get_json()
    nid = data.get('id')
    if nid:
        ni = Notifications.query.get(nid)
        if (not ni) or (ni.user_id != current_user):
            return APIResponse.error("Notification not found", 400)
        if ni.read == 0:
            ni.read = 1
            db.session.commit()
            return APIResponse.success("Notification marked as read", 200)
        else:
            return APIResponse.success("Notification already marked as read", 200)
    else:
        return APIResponse.error("Notification ID is required", 400)

@app.route('/remove_notification', methods=['POST'])
@jwt_required()
def remove_notification():
    current_user = get_jwt_identity()
    data = request.get_json()
    user = User.query.get(current_user)
    if not user:
        return APIResponse.error("User not found", 400)
    nid = data.get('id')
    if nid:
        ni = Notifications.query.get(nid)
        if (not ni) or (ni.user_id != current_user):
            return APIResponse.error("Notification not found", 400)
        db.session.query(Notifications).filter_by(id=nid).delete()
        db.session.commit()
        return APIResponse.success("Notification removed successfully", 200)
    else:
        return APIResponse.error("Notification ID is required", 400)