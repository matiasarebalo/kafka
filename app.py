from flask import Flask, render_template, request, g, redirect, url_for
from flask_cors import CORS
#from models import create_post, get_posts
#from data import get_registered_user
#from kafka import KafkaProducer
import json
import time
app = Flask(__name__)

CORS(app)

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
def home():
	return render_template('home/home.html')

@app.route('/login', methods=['GET','POST'])
def log_in():
	if request.method == 'GET':
		return render_template("home/log_in.html")	
	if request.method == 'POST':
		#... logica del login
		return redirect(url_for("index"))

@app.route('/signin', methods=['GET','POST'])
def sig_in():
	if request.method == 'GET':
		return render_template("home/sign_in.html")	
	if request.method == 'POST':
		#... logica para registrarse
		return redirect(url_for("index"))


# Users functionality
@app.route('/news')
def news():
	return render_template('users/news.html')

@app.route('/publish')
def publish():
	return render_template('users/publish.html')

@app.route('/search_users')
def search_users():
	return render_template('users/search_users.html')

@app.route('/profile')
def profile():
	return render_template('users/profile.html')

@app.route('/followers')
def followers():
	return render_template('users/followers.html')

@app.route('/following')
def following():
	return render_template('users/following.html')

@app.route('/posts/<idPost>', methods=['GET'])
def post(idPost):
	return render_template('posts/post.html')


if __name__=='__main__':
	#app.run(port=8081)
	app.run(debug=True)
