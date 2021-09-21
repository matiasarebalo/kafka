from flask import Flask, render_template, request, g, redirect, url_for, flash, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
import time
import base64
import os

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager 
from flask_login import login_required, current_user, login_user, logout_user
from flask_marshmallow import Marshmallow

from schemas.user import UserSchema
from schemas.post import PostSchema

# Para la creacion del topic cuando se registra un nuevo usuario en el sistema
from kafka import KafkaProducer, KafkaConsumer, producer
from kafka.admin import KafkaAdminClient, NewTopic

admin_client = KafkaAdminClient(bootstrap_servers="localhost:9092", client_id="prueba", api_version=(0, 10, 1))
topic_list = []

app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/kafka'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'log_in'
login_manager.init_app(app)

#subs = db.Table('subs', db.Column('user_id', db.ForeignKey('user.id')),
#db.Column('me_id', db.ForeignKey('me.id')))

class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(100), unique=True)
	password = db.Column(db.String(100))
	name = db.Column(db.String(1000))
	posts = db.relationship('Post', backref='user', lazy='dynamic')
	subscribers= db.relationship('Me', backref='user', lazy= 'dynamic')

class Me(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	followname = db.Column(db.String(1000))
	followid = db.Column(db.Integer)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Post(db.Model):
	id = db.Column(db.Integer,  primary_key=True, autoincrement=True)
	img = db.Column(db.String(100), nullable=True)
	text = db.Column(db.Text)
	title = db.Column(db.String(64))
	iduser = db.Column(db.String(64))
	date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

db.create_all()

user_schema = UserSchema()

users_schema = UserSchema(many=True)

post_schema = PostSchema()

posts_schema = PostSchema(many=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def json_serializer(data):
    return json.dumps(data).encode("utf-8")

# Home. 
@app.route('/')
@login_required
def home():
	username = current_user.username
	results = users_schema.dump(User.query.filter(User.username!=username))
	posts = posts_schema.dump(Post.query.all())
	return render_template('home/home.html', user = current_user, all_users = results, posts = posts )

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
	posts = posts_schema.dump(Post.query.all())
	return render_template('users/news.html', posts = posts)


@app.route('/publish' , methods=['POST'])
@login_required
def upload():
	title= request.form['title']
	text = request.form['text']
	id_user = User.query.filter_by(username=current_user.username).first().id
	file = request.files['inputFile']
	filename = secure_filename(file.filename)
	try:
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
		img = Post(title=title, iduser=id_user, text=text, img=filename, user_id=current_user.id)
	except:
		print("No hay foto")
		img = Post(title=title, iduser=id_user, text=text, img=None, user_id=current_user.id)
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
	posts = Post.query.filter_by(iduser=current_user.id)
	return render_template('users/profile.html' , user = current_user, posts = posts_schema.dump(posts))

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
	post = Post.query.filter_by(id=idPost).first()
	print(post_schema.dump(post))
	return render_template('posts/post.html', user = current_user, post = post_schema.dump(post))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
	username=request.args.get('search')
	users = User.query
	users = users.filter(User.name.like('%' + username + '%'))
	users = users.order_by(User.name).all()
	return jsonify(users_schema.dump(users))

@app.route('/verPerfil', methods=['GET', 'POST'])
@login_required
def verPerfil():
	username=request.form['usuarioBuscado']
	user = User.query.filter_by(username=username).first()
	if(user):
		posts = Post.query.filter_by(iduser=user.id)
		return render_template('users/profile.html' , user = user_schema.dump(user), posts = posts_schema.dump(posts))
	else:
		results=users_schema.dump(User.query.all())
		return render_template('home/home.html', user=current_user, all_users = results)


@app.route('/like', methods=['POST'])
@login_required
def like():
	id_post=request.form['idPost']
	

	return redirect(url_for("home"))

@app.route('/follow', methods=['POST'])
@login_required
def follow():
	username=request.form['usuarioBuscado']
	follow_id = User.query.filter_by(username=username).first().id
	id_user = User.query.filter_by(username=current_user.username).first().id
	# Creacion de la particion dentro del topic/usuario
	producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=json_serializer)
	# nombre.username es el topic donde publica y el string que sigue es lo que se guarda
	producer.send(username, "{} Te sigue".format(current_user.username))
	
	print(follow_id)
	# Aca va el codigo para seguir al usuario al usuario
	me = Me(followname=username, user_id=id_user,followid=follow_id)
	db.session.add(me)
	db.session.commit()

	#
	return redirect(url_for("home"))

if __name__=='__main__':
	#app.run(port=8081)
	app.run(debug=True)