from flask import Flask, render_template, request, g, redirect, url_for, flash, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
import os

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager 
from flask_login import login_required, current_user, login_user, logout_user

from schemas.user import UserSchema
from schemas.post import PostSchema
from schemas.me import MeSchema

# Para la creacion del topic cuando se registra un nuevo usuarion en el sistema
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic

admin_client = KafkaAdminClient(bootstrap_servers="localhost:9092", client_id="prueba", api_version=(0, 10, 1))
notificaciones_user = []
posts_followed = []

app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/kafka'
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

me_schema = MeSchema()

mes_schema = MeSchema(many=True)


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
	amigos_sugeridos = users_schema.dump(User.query.filter(User.username!=username))
	me_ = mes_schema.dump(Me.query.filter(Me.user_id==current_user.id))
	
	for m in me_:
		for user in	users_schema.dump(User.query.filter(User.username!=username)):
			if(m['followname'] == user['username']):
				amigos_sugeridos.remove(user)

	print(amigos_sugeridos)

	posts = []

	if len(me_) != 0:
		for topics in me_:

			elemento = posts_schema.dump(Post.query.filter(Post.user_id == topics["followid"]))
			if len(elemento) != 0:
				print("")
				posts = posts + elemento

		posteosDelUserLogueado = posts_schema.dump(Post.query.filter(Post.user_id == current_user.id))
		if len(posteosDelUserLogueado) != 0:
			posts = posts + posteosDelUserLogueado

	else:
		posts = posts_schema.dump(Post.query.filter(Post.user_id == current_user.id))

	posts.sort(key=id, reverse=True)

	return render_template('home/home.html', user = current_user, amigos_sugeridos = amigos_sugeridos, posts = posts)



def get_notificaciones():
	# Topic con las notificaciones del usuario logueado
	username = current_user.username
	notificaciones = []
	topic_notif = username + '_notificaciones'

	consumer_notificaciones = KafkaConsumer(bootstrap_servers=['localhost:9092'], consumer_timeout_ms=1000)

	# Topic del propio usuario para saber si alguien le dio like o lo sigue 
	notificaciones.append(topic_notif)
	tp_usr = TopicPartition(topic=topic_notif, partition=0)

	consumer_notificaciones.assign([tp_usr])			# Asigna el topic al consumidor

	consumer_notificaciones.seek_to_end(tp_usr)			# Busca el final de la lista
	fin = consumer_notificaciones.position(tp_usr)		# Guarda la posicion del ultimo registro
	consumer_notificaciones.seek_to_beginning(tp_usr)	# Vuelve al inicio de la lista

	# Lista para guardar los registros traidos de kafka
	nt = []

	for notificacion in consumer_notificaciones:		# Itera entre todos los registros del topic seleccionado
		nt.append(notificacion)							# Agrega en la lista todos los registros del topic
		if fin == notificacion.offset:					# Sale del for cuando llega al final de la lista y no espera por nuevos mensajes
			break

	notificaciones_user = nt

	notificaciones_user.reverse()
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
		tl1 = []
		tl1.append(NewTopic(name=username, num_partitions=1, replication_factor=1))
		admin_client.create_topics(new_topics=tl1, validate_only=False)

		# Creacion del topic para notificaciones (Donde escriben los likes y seguidores nuevos)
		tl2 = []
		topic_notif = username + '_notificaciones'
		tl2.append(NewTopic(name=topic_notif, num_partitions=1, replication_factor=1))
		admin_client.create_topics(new_topics=tl2, validate_only=False)

		return redirect(url_for("home"))

@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for("log_in"))

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
	posts = Post.query.filter_by(iduser=current_user.id)
	return render_template('users/profile.html' , user = current_user, posts = posts_schema.dump(posts))

@app.route('/<username>/followings')
@login_required
def following(username):
	user = user_schema.dump(User.query.filter(User.username==username).one())
	following = mes_schema.dump(Me.query.filter(Me.user_id==user['id']).all())
	return render_template('users/following.html', following=following)

@app.route('/<username>/followers')
@login_required
def followers(username):
	followers = mes_schema.dump(Me.query.filter(Me.followname==username).all())
	print(followers)
	return render_template('users/followers.html', followers=followers)

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
		esta_siguiendo = mes_schema.dump(Me.query.filter(Me.user_id==current_user.id).filter(Me.followname==username))
		return render_template('users/profile.html' , user = user_schema.dump(user), posts = posts_schema.dump(posts), esta_siguiendo = esta_siguiendo)
	else:
		results=users_schema.dump(User.query.all())
		return render_template('home/home.html', user=current_user, all_users = results)


@app.route('/like', methods=['POST'])
@login_required
def like():
	nombre = current_user.username
	titulo = request.form['title'][:30]+"..." if len(request.form['title'])>30 else request.form['title']+"..."
	autor = request.form['usuarioBuscado'] # Nombre del usuario que creo el post
	topic_notif = autor + '_notificaciones'	# Topic del autor donde notifica

	producer = KafkaProducer(bootstrap_servers=['localhost:9092'], value_serializer=json_serializer)
	producer.send(topic_notif, f"A {nombre} le gusto tu publicacion: {titulo}")
	producer.close()

	return redirect(url_for("home"))

@app.route('/follow', methods=['POST'])
@login_required
def follow():
	username=request.form['usuarioBuscado']
	follow_id = User.query.filter_by(username=username).first().id
	id_user = User.query.filter_by(username=current_user.username).first().id
	
	# Aca va el codigo para seguir al usuario al usuario
	if Me.query.filter_by(user_id=id_user, followid=follow_id).first() is None:
		me = Me(followname=username, user_id=id_user,followid=follow_id)
		db.session.add(me)
		db.session.commit()

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
		producer.send(topic_notif, f"{nombre.username} comenzo a seguirte.")
		producer.close()
	else:
		flash("Usted ya sigue a este usuario")
	return redirect(url_for("home"))

@app.route('/notifications', methods=['GET'])
@login_required
def notifications():
	get_notificaciones()
	return render_template('users/notifications.html', notif=notificaciones_user)


if __name__=='__main__':
	app.run(debug=True)