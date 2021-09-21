from threading import local
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

from flask_socketio import SocketIO, emit
import uuid
import asyncio
from multiprocessing import Process

# Para la creacion del topic cuando se registra un nuevo usuarion en el sistema
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic

admin_client = KafkaAdminClient(bootstrap_servers="localhost:9092", client_id="prueba", api_version=(0, 10, 1))
topic_list = []
notificaciones_user = []
posts_followed = []

app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:20101990@localhost/kafka'
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
	username = current_user.username
	results=users_schema.dump(User.query.filter(User.username!=username))

	get_notificaciones()

	return render_template('home/home.html', user=current_user, all_users = results, notif=notificaciones_user)

def get_notificaciones():
	# Topic con las notificaciones del usuario logueado
	username = current_user.username
	notificaciones = []
	topic_notif = username + '_notificaciones'

	consumer_notificaciones = KafkaConsumer(bootstrap_servers=['localhost:9092'], consumer_timeout_ms=1000)

	# Topic del propio usuario para saber si si alguien le dio like o lo sigue 
	notificaciones.append(topic_notif)
	tp_usr = TopicPartition(topic=topic_notif, partition=0)

	consumer_notificaciones.assign([tp_usr])

	consumer_notificaciones.seek_to_end(tp_usr)
	fin = consumer_notificaciones.position(tp_usr)
	consumer_notificaciones.seek_to_beginning(tp_usr)

	for notificacion in consumer_notificaciones:
		notificaciones_user.append(notificacion)
		if fin == notificacion.offset:
			break

	consumer_notificaciones.close()

def get_post_kafka():
	# Topic con las notificaciones para posts nuevos
	username = current_user.username
	followed = [] # Cargar con los usuarios a los que sigue
	tp_usr = []
	consumer_posts = KafkaConsumer(bootstrap_servers=['localhost:9092'], consumer_timeout_ms=1000)

	# Topic del propio usuario para saber si si alguien le dio like o lo sigue
	for usr in followed:
		tp_usr.append(TopicPartition(topic=usr, partition=0))
	
	consumer_posts.assign(tp_usr)

	for tp in tp_usr:
		consumer_posts.seek_to_end(tp)
		fin = consumer_posts.position(tp)
		consumer_posts.seek_to_beginning(tp)

		for posts in consumer_posts:
			posts_followed.append(posts)
			if fin == posts.offset:
				break

	consumer_posts.close()

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

		# Creacion del topic correspondiente al usuario que se registra para guardar sus posteos
		topic_list.append(NewTopic(name=username, num_partitions=1, replication_factor=1))
		admin_client.create_topics(new_topics=topic_list, validate_only=False)

		# Creacion del topic para notificaciones (Donde escriben los likes y seguidores nuevos)
		topic_notif = username + '_notificaciones'
		topic_list.append(NewTopic(name=topic_notif, num_partitions=1, replication_factor=1))
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
	producer.send(current_user.username, "Nuevo post")
	producer.close()

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
	return render_template('posts/post.html', user=current_user)

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
		results=users_schema.dump(User.query.all())
		return render_template('home/home.html', user=current_user, all_users = results)

@app.route('/follow', methods=['POST'])
def follow():
	username=request.form['usuarioBuscado']
	user_id = User.query.filter_by(username=username).first().id

	# Agrega a la lista de seguidores al usuario logueado
	nombre = current_user
	topic_notif = username + '_notificaciones'
	consumer = KafkaConsumer(group_id=nombre.username, bootstrap_servers=['localhost:9092'], consumer_timeout_ms=1000)
	tp = TopicPartition(username, 0)
	consumer.assign([tp])

	consumer.seek_to_end(tp)
	last_offset = consumer.position(tp)
	consumer.seek_to_beginning(tp)

	for m in consumer:
		if m.offset == last_offset - 1:
			break

	consumer.close()

	# Envía la notificación al usuario al que comenzó a seguir
	producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=json_serializer)
	producer.send(topic_notif, "Comenzo a seguirte " + nombre.username)
	producer.close()

	return redirect(url_for("home"))

if __name__=='__main__':
	app.run(debug=True)