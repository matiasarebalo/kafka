from flask import Flask, render_template, request
from flask_cors import CORS
from models import create_post, get_posts
#from data import get_registered_user
from kafka import KafkaProducer
import json
import time
app = Flask(__name__)

CORS(app)

def json_serializer(data):
    return json.dumps(data).encode("utf-8")

producer =KafkaProducer(bootstrap_servers=['127.0.0.1:9092'],
                        value_serializer=json_serializer)

def get_registered_user(name,post):
        return{
        "name" : name,
        "address" : post
        }



@app.route('/', methods=['GET','POST'])
def index():
	
	if request.method == 'GET':
		pass	
	if request.method == 'POST':
		name = request.form.get('name')
		post = request.form.get('post')
		registered_user = get_registered_user(name, post)
		print(registered_user)
		producer.send("registered_user",registered_user) 
        #time.sleep(4)
	
	posts = get_posts()	

	return render_template('index.html',posts=posts)
	
if __name__=='__main__':
	#app.run(port=8081)
	app.run(debug=True)
