from flask import request
from flask_jwt_extended import jwt_required
from app import app, db
from sqlalchemy import func
from app.models import Notes
from app.utils import APIResponse, check_data
from app.security import access_control
import os
from urllib.parse import quote

@app.route('/add_notes', methods=['POST'])
@jwt_required()
@access_control(check_form_data=['title', 'meeting_type', 'description','students','read_members','edit_members'])
def add_notes(user):
    data = dict(request.form)
    for k in ['students','read_members','edit_members']: data[k] = eval(data[k])
    if user.id not in data['edit_members']:
        data['edit_members'].append(user.id)
    if user.id in data['read_members']:
        data['read_members'].remove(user.id)
    note = Notes(**data)
    db.session.add(note)
    db.session.commit()
    attachments = {}
    for ffile in request.files.getlist('attachments'):
        print(ffile)
        fp = os.path.join("app/static/notes/", str(note.id)+"_"+ffile.filename)
        ffile.save(fp)
        attachments[ffile.filename] = f"{app.config['BACKEND_URL']}/static/notes/{note.id}_{quote(ffile.filename)}"
    note.attachments = attachments
    db.session.commit()
    return APIResponse.success("Note created", 201)

@app.route('/get_notes', methods=['GET'])
@jwt_required()
@access_control()
def get_notes(user):

    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    sort_by = request.args.get('sort_by', default='due', type=str)
    sort_order = request.args.get('sort_order', default='asc', type=str)
    search_query = request.args.get('search')
    
    if sort_order not in ['asc', 'desc']:
        return APIResponse.error("Invalid sort order", 400)

    query = Notes.query.filter((func.json_contains(Notes.read_members, str(user.id))) | (func.json_contains(Notes.edit_members, str(user.id))))

    student_id = request.args.get('student_id')
    if student_id:
        query = query.filter(func.json_contains(Notes.students, str(student_id)))

    if search_query:
        query = query.filter(Notes.title.ilike(f"%{search_query}%"))

    if hasattr(Notes, sort_by):
        column = getattr(Notes, sort_by)
        query = query.order_by(column.asc() if sort_order == 'asc' else column.desc())
    else:
        return APIResponse.error("Invalid sort column", 400)
    
    paginated_notes = query.paginate(page=page, per_page=per_page)
    return APIResponse.success(
        "Success",
        200,
        data=[{**note.nt_to_json(), "access_type": 1 if user.id in note.edit_members else 0} for note in paginated_notes.items],
        pagination={
            'page': paginated_notes.page,
            'per_page': paginated_notes.per_page,
            'total_pages': paginated_notes.pages,
            'total_items': paginated_notes.total,
        }
    )

@app.route('/get_note', methods=['POST'])
@jwt_required()
@access_control(note="")
def get_note(user, data, note):
    data = {**note.nt_to_json(), "access_type": 1 if user.id in note.edit_members else 0}
    return APIResponse.success("Success", 200, data=data)

@app.route('/edit_note', methods=['POST'])
@jwt_required()
@access_control(note="")
def edit_note(user, data, note):
    mfr = check_data(data, ['id'])
    if mfr: return mfr
    
    data = dict(request.form)
    for k in ['students','read_members','edit_members', 'remove_attachments']: 
        if k in data: 
            data[k] = eval(data[k])

    if 'edit_members' in data and data['edit_members'] == []:
        return APIResponse.error("Note must have one assignee", 404)
    
    attachments = note.attachments

    if request.files.getlist('add_attachments'):
        for ffile in request.files.getlist('add_attachments'):
            fp = os.path.join("app/static/notes/", str(note.id)+"_"+ffile.filename)
            ffile.save(fp)
            attachments[ffile.filename] = f"{app.config['BACKEND_URL']}/static/notes/{note.id}_{quote(ffile.filename)}"
    
    if 'remove_attachments' in data:
        for ffile in data['remove_attachments']:
            os.remove(os.path.join(f"app/static/notes/{note.id}_{ffile}"))
            del attachments[ffile]
        del data['remove_attachments']
    
    for key, value in data.items():
        setattr(note, key, value)
    
    db.session.commit()

    note.attachments = attachments
    db.session.commit()
    return APIResponse.success("Note Updated Successfully", 200)

@app.route('/remove_note', methods=['POST'])
@jwt_required()
@access_control(note="")
def remove_note(user, data, note):
    for ffile in note.attachments:
        os.remove(os.path.join(f"app/static/notes/{note.id}_{ffile}"))
    db.session.delete(note)
    db.session.commit()
    return APIResponse.success("Note Deleted Successfully", 200)