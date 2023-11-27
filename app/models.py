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
    plan = db.Column(db.Integer, db.ForeignKey('plans.id'))

    def set_password(self, password):
        self.pw = generate_password_hash(password, method = "pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.pw, password)
    
class Plans(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    perm = db.Column(db.JSON)

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

    def ie_to_json(self):
        return {'id':self.id, 'name':self.name, 'campus_type':self.campus_type, 'address':self.address, 'district':self.district, 'city':self.city, 'state':self.state, 'country':self.country, 'zipcode':self.zipcode}

class UserInstitute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ins_id = db.Column(db.Integer, db.ForeignKey('institute.id'))
    role = db.Column(db.Integer, default=2)
    token = db.Column(db.String(16))