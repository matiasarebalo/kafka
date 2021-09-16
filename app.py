from flask import Flask, render_template, request, g, redirect, url_for, flash, jsonify
from flask_cors import CORS
#from models import create_post, get_posts
#from data import get_registered_user
#from kafka import KafkaProducer
import json
import time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager 
from flask_login import login_required, current_user, login_user, logout_user
from flask_marshmallow import Marshmallow
app = Flask(__name__)

CORS(app)

app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/kafka'
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

'''
producer =KafkaProducer(bootstrap_servers=['127.0.0.1:9092'],
                        value_serializer=json_serializer)

def get_registered_user(name,post):
        return{
        "name" : name,
        "address" : post
        }

'''

# Deberia borrarse y pasar a home() (o usarse como home)
@app.route('/', methods=['GET','POST'])
def index():
	
	if request.method == 'GET':
		pass	
	if request.method == 'POST':
		name = request.form.get('name')
		post = request.form.get('post')
		#registered_user = get_registered_user(name, post)
		#print(registered_user)
		#producer.send("registered_user",registered_user) 
        #time.sleep(4)
	
	posts = [] #get_posts()	

	return render_template('index.html',posts=posts)
	

# Home. 
# TODO: Hay que cambiar el endpoint a '/' cuando eliminemos index()
@app.route('/home')
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

	if request.method == 'POST':
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

	if request.method == 'POST':
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

		return redirect(url_for("home"))

@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for("log_inc"))

# Users functionality
@app.route('/news')
@login_required
def news():
	return render_template('users/news.html')

@app.route('/publish')
@login_required
def publish():
	return render_template('users/publish.html')

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


if __name__=='__main__':
	#app.run(port=8081)
	app.run(debug=True)
