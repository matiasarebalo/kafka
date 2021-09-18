from flask_login import UserMixin
from datetime import datetime
import base64



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

class Img(db.Model):
    id = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    img = db.Column(db.Text,unique=True, nullable=False) 
    mimetype = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text)
    title= db.Column(db.String(64))
    location = db.Column(db.String(64))
    pic_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FileContent(db.Model):
    id = db.Column(db.Integer,  primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False) #Actual data, needed for Download
    rendered_data = db.Column(db.Text, nullable=False)#Data to render the pic in browser
    text = db.Column(db.Text)
    location = db.Column(db.String(64))
    pic_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
def __repr__(self):
    return f'Pic Name: {self.name} Data: {self.data} text: {self.text} created on: {self.pic_date} location: {self.location}'
