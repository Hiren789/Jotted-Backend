from app import db
from werkzeug.security import generate_password_hash, check_password_hash

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
        return -1 if reqq is None else reqq.role_id        

    def set_password(self, password):
        self.pw = generate_password_hash(password, method = "pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.pw, password)

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

    def ie_to_json(self):
        return {'id':self.id, 'name':self.name, 'campus_type':self.campus_type, 'address':self.address, 'district':self.district, 'city':self.city, 'state':self.state, 'country':self.country, 'zipcode':self.zipcode, 'ins_type':self.ins_type}

class UserInstitute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ins_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    role_id = db.Column(db.Integer, default=2)
    token = db.Column(db.String(16))

class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ins_id = db.Column(db.Integer, db.ForeignKey('institute.id'))