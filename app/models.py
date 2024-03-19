from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime
from app.utils import APIResponse, profile_image_url

class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.BigInteger, primary_key=True)
    state = db.Column(db.String(32))
    city = db.Column(db.String(32))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pre = db.Column(db.String(8))
    fn = db.Column(db.String(128))
    mn = db.Column(db.String(128))
    ln = db.Column(db.String(128))
    suf = db.Column(db.String(8))
    email = db.Column(db.String(128), index=True, unique=True)
    pn = db.Column(db.String(15), index=True, unique=True)
    pw = db.Column(db.String(128))
    plan = db.Column(db.JSON)
    pro_com = db.Column(db.Integer, default=0)
    last_ins = db.Column(db.Integer, db.ForeignKey('institute.id'))

    def get_institutes(self, cnt=False, role_id=None):
        query = (
            db.session.query(Institute, UserInstitute.role_id)
            .join(UserInstitute, Institute.id == UserInstitute.ins_id)
            .filter(UserInstitute.user_id == self.id, UserInstitute.role_id == role_id)
        ) if role_id else (
            db.session.query(Institute, UserInstitute.role_id)
            .join(UserInstitute, Institute.id == UserInstitute.ins_id)
            .filter(UserInstitute.user_id == self.id)
        )
        institutes = query.all()
        return len(institutes) if cnt else [{**institute.ie_to_json(), "role_id":role} for institute, role in institutes]
    
    def get_access_id(self, ins_id):
        reqq = UserInstitute.query.filter(UserInstitute.user_id == self.id, UserInstitute.ins_id == ins_id).first()
        return (-1, []) if reqq is None else (reqq.role_id, reqq.students)

    def set_password(self, password):
        self.pw = generate_password_hash(password, method = "pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.pw, password)
    
    def user_profile(self):
        return {"pre":self.pre, "fn":self.fn, "mn":self.mn, "ln":self.ln, "suf":self.suf, "email":self.email, "pn":self.pn, "plan":self.plan, "profile_pic": profile_image_url(self.id)}
    
    def member_profile(self):
        return {"id":self.id, "name":f"{self.fn} {self.ln}", "profile_pic": profile_image_url(self.id)}
    
    def new_notification(self, title, body):
        nn = Notifications(user_id = self.id, title = title, body = body)
        db.session.add(nn)
        db.session.commit()

class Institute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(256))
    campus_type = db.Column(db.String(32))
    address = db.Column(db.Text)
    district = db.Column(db.String(64))
    city = db.Column(db.String(64))
    state = db.Column(db.String(64))
    country = db.Column(db.String(64))
    zipcode = db.Column(db.String(16))
    ins_type = db.Column(db.Integer)
    campus_grade = db.Column(db.JSON)

    def ie_to_json(self):
        return {'id':self.id, 'name':self.name, 'campus_type':self.campus_type, 'address':self.address, 'district':self.district, 'city':self.city, 'state':self.state, 'country':self.country, 'zipcode':self.zipcode, 'ins_type':self.ins_type, 'campus_grade':self.campus_grade}
    
    def get_plan(self):
        owneruserins = db.session.query(UserInstitute).filter((UserInstitute.ins_id==self.id) & (UserInstitute.role_id==0)).first()
        return User.query.get(owneruserins.user_id).plan
    
    def cgexists(self, campus, grade):
        if campus not in self.campus_grade:
            return APIResponse.error(f"Campus not found in Institute Plan", 400)
        if grade not in self.campus_grade[campus]:
            return APIResponse.error(f"Grade not found in Institute and Campus Plan", 400)
    
    def verify_campus_grades(self, given_campus_grade):
        students = db.session.query(Student.campus_id,Student.grade).filter_by(ins_id = self.id).all()
        tmpvgs = {}
        for i in students:
            if i[1] not in tmpvgs.get(i[0],[]):
                tmpvgs[i[0]] = tmpvgs.get(i[0],[])+[i[1]]
        for i in tmpvgs:
            if i not in given_campus_grade:
                return APIResponse.error(f"Already used Campus {i} not found in new data", 400)
            else:
                for j in tmpvgs[i]:
                    if j not in given_campus_grade[i]:
                        return APIResponse.error(f"Already used grade {j} not found in Campus {i} in new data", 400)
        return None
    
    def get_students(self, cnt=False, stnds = None, campus_id = None, grade = None):
        students = db.session.query(Student).filter(Student.id.in_(stnds)) if stnds else db.session.query(Student).filter_by(ins_id = self.id)
        if campus_id:
            students = students.filter_by(campus_id = campus_id)
        if grade:
            students = students.filter_by(grade = grade)
        return len(students.all()) if cnt else [student.se_to_json() for student in students.all()]

class UserInstitute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ins_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    role_id = db.Column(db.Integer, default=2)
    students = db.Column(db.JSON)
    token = db.Column(db.String(16))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(32))
    middle_name = db.Column(db.String(32))
    last_name = db.Column(db.String(32))
    suffix = db.Column(db.String(8))
    gender = db.Column(db.String(16))
    email = db.Column(db.String(32))
    phone = db.Column(db.String(32))
    zipcode = db.Column(db.String(6))
    state = db.Column(db.String(32))
    country = db.Column(db.String(32))
    city = db.Column(db.String(32))
    extra_info = db.Column(db.JSON)

    ins_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    campus_id = db.Column(db.String(64))
    grade = db.Column(db.String(16))

    def se_to_json(self):
        return {
            'id':self.id, 
            'ins_id':self.ins_id, 
            'team_member': [x.user_id for x in self.get_team_members()],
            'campus_id': self.campus_id,
            'grade': self.grade,            
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'suffix': self.suffix,
            'gender': self.gender,
            'email': self.email,
            'phone': self.phone,
            'zipcode': self.zipcode,
            'state': self.state,
            'country': self.country,
            'city': self.city,
            'extra_info': self.extra_info
        }

    def se_profile(self):
        return {'id':self.id, 'name': f"{self.first_name} {self.last_name}"}
    
    def get_team_members(self):
        return db.session.query(UserInstitute).filter((UserInstitute.ins_id == self.ins_id) & (UserInstitute.role_id == 2)).filter(func.json_contains(UserInstitute.students, str(self.id))).all()

    def set_team_member_acess(self, usrs):
        exiusrs = {x.user_id:x for x in self.get_team_members()}
        delusrs = [x for x in exiusrs if x not in usrs]
        newusrs = [x for x in usrs if x not in exiusrs]
        
        for key, stund in exiusrs.items():
            if key in delusrs:
                tmpstnds = list(set(stund.students))
                tmpstnds.remove(self.id)
                stund.students = tmpstnds

        newusrs = UserInstitute.query.filter((UserInstitute.user_id.in_(newusrs)) & (UserInstitute.ins_id == self.ins_id) & (UserInstitute.role_id == 2))
        for k in newusrs:
            k.students = k.students+[self.id]
        
        db.session.commit()

class ArchivedStudent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(32))
    middle_name = db.Column(db.String(32))
    last_name = db.Column(db.String(32))
    suffix = db.Column(db.String(8))
    gender = db.Column(db.String(16))
    email = db.Column(db.String(32))
    phone = db.Column(db.String(32))
    zipcode = db.Column(db.String(6))
    state = db.Column(db.String(32))
    country = db.Column(db.String(32))
    city = db.Column(db.String(32))
    extra_info = db.Column(db.JSON)

    ins_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    campus_id = db.Column(db.String(64))
    grade = db.Column(db.String(16))

    def se_to_json(self):
        return {
            'id':self.id, 
            'ins_id':self.ins_id, 
            'campus_id': self.campus_id,
            'grade': self.grade,            
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'suffix': self.suffix,
            'gender': self.gender,
            'email': self.email,
            'phone': self.phone,
            'zipcode': self.zipcode,
            'state': self.state,
            'country': self.country,
            'city': self.city,
            'extra_info': self.extra_info
        }

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text)
    priority = db.Column(db.Integer)
    status = db.Column(db.String(32))
    due = db.Column(db.DateTime)
    students = db.Column(db.JSON)
    read_members = db.Column(db.JSON)
    edit_members = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def td_to_json(self):
        return {'id': self.id,'title': self.title,'body': self.body,'priority': self.priority,'status': self.status,'due': self.due.isoformat() if self.due else None,'students': self.students,'read_members': self.read_members,'edit_members': self.edit_members, 'created_at': self.created_at}

class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    meeting_type = db.Column(db.Text)
    description = db.Column(db.Text)


    attachments = db.Column(db.JSON)
    # priority = db.Column(db.Integer)
    # status = db.Column(db.String(32))
    # due = db.Column(db.DateTime)

    students = db.Column(db.JSON)
    read_members = db.Column(db.JSON)
    edit_members = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def nt_to_json(self):
        return {'id': self.id, 'title': self.title, 'meeting_type': self.meeting_type, 'description': self.description, 'attachments': self.attachments, 'students': self.students, 'read_members': self.read_members, 'edit_members': self.edit_members, 'created_at': self.created_at}
    
class Notifications(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(256))
    body = db.Column(db.Text)
    read = db.Column(db.Integer, default=0)

    def ne_to_json(self):
        return {'id':self.id, 'title':self.title, 'body':self.body}

def list_to_members(member_ids):
    usrs = User.query.filter(User.id.in_(member_ids)).all()
    return [x.member_profile() for x in usrs]

def list_to_students(student_ids):
    students = db.session.query(Student).filter(Student.id.in_(student_ids))
    return [student.se_profile() for student in students.all()]