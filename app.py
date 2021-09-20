from flask import Flask, render_template, request, g, redirect, url_for, flash, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
import time
import base64

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager 
from flask_login import login_required, current_user, login_user, logout_user
from flask_marshmallow import Marshmallow

# Para la creacion del topic cuando se registra un nuevo usuarion en el sistema
from kafka import KafkaProducer, producer
from kafka.admin import KafkaAdminClient, NewTopic

admin_client = KafkaAdminClient(bootstrap_servers="localhost:9092", client_id="prueba", api_version=(0, 10, 1))
topic_list = []

app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/kafka'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'log_in'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

class Img(db.Model):
	id = db.Column(db.Integer,  primary_key=True, autoincrement=True)
	name = db.Column(db.String(128), nullable=False)
	img = db.Column(db.LargeBinary(length=(2**32)-1), nullable=False) 
	mimetype = db.Column(db.Text, nullable=False)
	text = db.Column(db.Text)
	title = db.Column(db.String(64))
	iduser = db.Column(db.String(64))
	location = db.Column(db.String(64))
	pic_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

db.create_all()
ma = Marshmallow(app)

class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'username')

user_schema = UserSchema()
users_schema = UserSchema(many=True)

@login_manager.user_loader
def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

def json_serializer(data):
    return json.dumps(data).encode("utf-8")

# Home. 
@app.route('/')
@login_required
def home():
	if request.method == 'GET':
		all_users= User.query.all()
		results=users_schema.dump(User.query.all())
		print(results)
		return render_template('home/home.html', user=current_user, all_users = results)

# AUTH
@app.route('/login', methods=['GET','POST'])
def log_in():
	if request.method == 'GET':
		return render_template("auth/log_in.html")	
	elif request.method == 'POST':
		username = request.form.get('username')
		password = request.form.get('password')

		user = User.query.filter_by(username=username).first()

		if not user or not check_password_hash(user.password, password):
			flash('Invalid credentials.')
			return redirect(url_for('log_in')) 

		login_user(user)

		return redirect(url_for('home'))

@app.route('/signin', methods=['GET','POST'])
def sig_in():
	if request.method == 'GET':
		return render_template("auth/sign_in.html")	
	elif request.method == 'POST':
		username = request.form.get('username')
		name = request.form.get('name')
		password = request.form.get('password')
		user = User.query.filter_by(username=username).first()
		if user:
			flash('User already registered')
			return redirect(url_for('sig_in'))
		new_user = User(username=username, name=name, password=generate_password_hash(password, method='sha256'))
		db.session.add(new_user)
		db.session.commit()
		login_user(User.query.filter_by(username=username).first())
		# Creacion del topic correspondiente al usuario que se registra
		topic_list.append(NewTopic(name=username, num_partitions=1, replication_factor=1))
		admin_client.create_topics(new_topics=topic_list, validate_only=False)

		return redirect(url_for("home"))

@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for("log_in"))

# Users functionality
@app.route('/news')
@login_required
def news():
	return render_template('users/news.html')


@app.route('/publish' , methods=['POST'])
@login_required
def upload():
	pic = request.files['inputFile']
	title= request.form['title']
	text = request.form['text']
	location = request.form['location']
	filename = secure_filename(pic.filename)
	mimetype = pic.mimetype
	id_user = User.query.filter_by(username=current_user.username).first().id

	img = Img(img=base64.b64encode(pic.read()),mimetype=mimetype,title=title, iduser=id_user, name=filename,text=text, location=location )
	db.session.add(img)
	db.session.commit()
	# Creacion de la particion dentro del topic/usuario
	producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=json_serializer)
	# nombre.username es el topic donde publica y el string que sigue es lo que se guarda
	producer.send(current_user.username, "Nuevo post")
	
	return redirect(url_for("home"))

@app.route('/search_users')
@login_required
def search_users():
	return render_template('users/search_users.html')

@app.route('/profile')
@login_required
def profile():
	return render_template('users/profile.html' , user=current_user)

@app.route('/followers')
@login_required
def followers():
	return render_template('users/followers.html')

@app.route('/following')
@login_required
def following():
	return render_template('users/following.html')

@app.route('/posts/<idPost>', methods=['GET'])
@login_required
def post(idPost):
	return render_template('posts/post.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
	username=request.args.get('search')
	users = User.query
	users = users.filter(User.name.like('%' + username + '%'))
	users = users.order_by(User.name).all()
	return jsonify(users_schema.dump(users))


@app.route('/verPerfil', methods=['GET', 'POST'])
def verPerfil():
	username=request.form['usuarioBuscado']
	users = User.query.filter_by(username=username).first()
	if(users):
		return render_template('users/profile.html' , user=users)
	else:
		all_users= User.query.all()
		results=users_schema.dump(User.query.all())
		return render_template('home/home.html', user=current_user, all_users = results)

@app.route('/follow', methods=['POST'])
def follow():
	username=request.form['usuarioBuscado']
	user_id = User.query.filter_by(username=username).first().id
	print(user_id)
	# Aca va el codigo para seguir al usuario al usuario
	#
	#
	return redirect(url_for("home"))

if __name__=='__main__':
	#app.run(port=8081)
	app.run(debug=True)