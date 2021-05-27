from flask import Blueprint, request, render_template, Flask, redirect, jsonify, Response, send_file, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
import io
from wsgiref.util import FileWrapper
from sqlalchemy import func
from hashlib import md5
from zlib import decompress
from flask_socketio import SocketIO, send, emit, join_room, leave_room
import base64
import socket
import threading
import time
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

class computer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.TEXT)

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
    all_computers = []
    for i in range(0, len(computer.query.all())):
        all_computers.append(computer.query.all()[i].id)
    return render_template("index.html", computer_list_nev=all_computers)

''' Client '''

file_cl = "" # The frame that the client sends.
pos_x = {} # the X position of the mouse on the img
pos_y = {} # the Y position of the mouse on the img
lock = {} # Variable that indicates on wether to lock the screen or not.

@app.route('/computers/<int:id>')
@login_required
def root(id):
    return render_template('computer.html')


def add_computer(mac_address, new_id):
    print(mac_address)
    print(new_id)
    new_user = computer(mac_address=mac_address, id=new_id)
    db.session.add(new_user)
    db.session.commit()
    return str(new_id)

#verify_login
@app.route('/computers/verify_login', methods=['POST', 'GET'])
def check_if_user_exists():
    if request.method == 'POST':
        js = request.get_json()
        print(js)
        if js is not None:
            mac_address = js['mac_address']
            print("MAC: " + mac_address)
            print(len(computer.query.all()))
            check_zero_computers = 0 # if there are 0 computers the for loop won't even happend.
            if len(computer.query.all()) == 0:
                print("1")
                check_zero_computers = 1
            else:
                check_zero_computers = 0

            for i in range(0,len(computer.query.all()) + check_zero_computers):
                print("In")
                if check_zero_computers == 0:
                    print("checking i")
                    current_id = computer.query.all()[i].id
                    current_mac = computer.query.all()[i].mac_address
                elif check_zero_computers == 1:
                    print("No comp")
                    current_id = 0
                    current_mac = 0
                if mac_address == current_mac:
                    print("True!")
                    return str(current_id)
            print("Not found")
            new_id = len(computer.query.all()) + 1
            return add_computer(mac_address, new_id)
        else:
            print("Empty, bad request")
    else:   
        return ""


@socketio.on('join')
def on_join(data):
    room = data['room']
    print("joined room " + room)
    join_room(room)

@app.route("/represent_file/<int:id>", methods=['GET'])
def re_file(id):
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


@app.route("/get_file/<int:id>", methods=['POST'])
def get_file(id):
    '''
    A function that sends the client when to ask for the new picture.
    '''
    if request.method == "POST":
        global file_cl
        t_file = request.data
        file_cl = t_file
        try:
            base64_encoded_img = base64.b64encode(file_cl)
            base64_img = base64_encoded_img.decode('utf-8')
            socketio.emit("get-file", {
                "data": "OK"}, room=str(id))  # The reason I am using socketio in here is so that I'll know when to ask for the new image.
        except:
            return "Err"
        return "200 OK"


@app.route("/info/<int:id>", methods=['POST'])
def info(id):
    data = request.get_json()
    running_procs = data["running processes"]
    search_history = data["chrome history"]
    formatted_procs = ""
    formatted_history = ""
    for process in running_procs:
        formatted_procs = formatted_procs + "--- PID: " + str(process["pid"]) + " --- " + "Name: " + str(process["name"]) + "--0" + "<br>"
    for history_tuple in search_history:
            formatted_history = formatted_history + "URL: " + history_tuple[0] + " DATE: " + history_tuple[1] + "<br>"
            # formatted_history = formatted_history + "Date: " + date + " URL: " + url
    # print(formatted_history)
    socketio.emit("info", {"procs": formatted_procs, "history" : formatted_history}, room=str(id))
    return "200 OK"


@socketio.on("pic click")
def pic_click(data):
    global pos_x
    global pos_y
    pos_x = data["posX"]
    pos_y = data["posY"]
    print(pos_x)

@socketio.on("lock")
def lock_client(data):
    global lock
    lock = data["lock"]

"""@app.route("/action", methods=["POST"])
def action():"""

def so():
    global pos_x
    global pos_y
    global lock
    prev_lock = "False"
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
            position = f'["{pos_x}", "{pos_y}"]' # formatting the string as a list
            c.send(position.encode()) # sending data to the client
            pos_x = "" # restting the variables so it wont send it all the time.
            pos_y = ""
        if lock != prev_lock and len(lock) != 0:
            print(lock)
            if lock == "True":
                c.send("Lock".encode())
            else:
                c.send("Unlock".encode())
            prev_lock = lock
        
        

if __name__ == '__main__':
    socketio_func = functools.partial(socketio.run, app, host="0.0.0.0")
    threading.Thread(target=socketio_func).start()
    threading.Thread(target=so, daemon=True).start()
    # socketio.run(app, host="0.0.0.0", debug=True)

