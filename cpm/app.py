from flask import Blueprint, request, render_template, Flask, redirect, jsonify, Response, send_file, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
import io
from wsgiref.util import FileWrapper
from sqlalchemy import func
from hashlib import md5
from zlib import decompress
from flask_socketio import SocketIO, send, emit
import base64
from threading import Thread
from zlib import decompress
from requests_toolbelt import MultipartEncoder

def create_app():
    app = Flask(__name__, template_folder='cmp_screen/templates')
    return app

app = create_app()
app.config['SECRET_KEY'] = "SECRETT$2"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db3.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
login_manager = LoginManager()
login_manager.init_app(app)
db = SQLAlchemy(app)
socketio = SocketIO(app)
class users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.TEXT)
    password = db.Column(db.TEXT)
    email = db.Column(db.TEXT)

@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

@app.route("/login", methods=["GET","POST"])
@login_manager.unauthorized_handler
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        check_box = request.form['CheckBox']
        print(check_box)
        print(check_box)
        user_check = bool(users.query.filter_by(username=username).first())
        pass_check = bool(users.query.filter_by(password=md5(password.encode("utf-8")).hexdigest()).first())
        if user_check and not pass_check:
            return "password"
        elif not user_check:
            return "username"
        else:
            user = users.query.filter_by(username=username,password=md5(password.encode("utf-8")).hexdigest()).first()
            db.session.commit()
            app.permanent_session_lifetime = False
            if check_box == "True": #always true for now
                login_user(user, remember=True)
            elif check_box == "False": #disabled for now
                login_user(user, remember=False)
            else:
                return "An unexpected error has occurred"
            return "Great"    
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect('/')
        else:
            return render_template('/login.html')

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        print(username)
        user_check = bool(users.query.filter(func.lower(users.username) == func.lower(username)).first())
        email_check = bool(users.query.filter_by(email=email).first())
        
        if (email_check) and (email[-10:] not in "@gmail.com" or email.count("@gmail.com") > 1) and user_check:
            print("all")
            return "all"
        elif user_check and (email[-10:] not in "@gmail.com" or email.count("@gmail.com") > 1):
            print("u e c")
            return "username exist email contain"
        elif user_check and email_check:
            print("u e e")
            return "username exist email exist"
        elif email_check:
            return "email exist"
        elif email[-10:] not in "@gmail.com" or email.count("@gmail.com") > 1:
            return "email contain"
        elif user_check:
            return "username exist"
        else:
            new_user = users(username = username, password=md5(password.encode("utf-8")).hexdigest(), email=email)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect('/')
        else:
            return render_template('/register.html')

@app.route("/")
@login_required
def index():
    return render_template("index.html")

''' Client '''

global file_cl


@app.route('/computer')
@login_required
def root():
  return render_template('computer.html')

@app.route("/represent_file",  methods=['GET'])
def re_file():
    if request.method == "GET":
        global file_cl
        try:
            base64_encoded_img = base64.b64encode(file_cl)
            base64_img = base64_encoded_img.decode('utf-8')
            return base64_img
        except:
            return "Err"

@app.route("/get_file", methods=['POST'])
def get_file():
    if request.method == "POST":
        global file_cl
        t_file = request.data
        file_cl = t_file
        socketio.emit("get-file", {"data" : "Ok"}) # The reason I am using socketio in here is so that I'll know when to ask for the new image.
        return "200 OK"


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)