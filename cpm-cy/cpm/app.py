from operator import pos
from flask import request, render_template, Flask, redirect, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from hashlib import md5
from zlib import decompress
from flask_socketio import SocketIO, send, emit, join_room
import base64
import socket
import threading
import itertools
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
    level = db.Column(db.INTEGER, default=1) # level 1 - regular employee, level 2 - Team leader, level 3 - Manager
    allow_to_view_level_2 = db.Column(db.TEXT, default="None")
    computer_id = db.Column(db.INTEGER, default=-1)


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
        amount_of_users = 0
        for i in range(0,len(users.query.all())):
            amount_of_users = amount_of_users + 1
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
            if amount_of_users > 0:
                new_user = users(username=username, password=md5(password.encode("utf-8")).hexdigest(), email=email)
            else:
                new_user = users(username=username, password=md5(password.encode("utf-8")).hexdigest(), email=email, level=3)
            db.session.add(new_user)
            db.session.commit()
            return redirect('/')
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect('/')
        else:
            return render_template('/register.html')


def get_admin_panel_data():
    '''
    The following function extacts all the data from the DB to show to the admin.
    '''
    users_username = []
    computer_client_id = []
    computers_mac = []
    assigned_values = []
    levels = []
    assigned_level_2_allowed_to_view = []
    for i in range(0,len(users.query.all())):
        users_username.append(users.query.all()[i].username)
        levels.append(users.query.all()[i].level)
        if users.query.all()[i].level == 2:
            assigned_level_2_allowed_to_view.append(users.query.all()[i].allow_to_view_level_2)
        else:
            assigned_level_2_allowed_to_view.append("None")
        if users.query.all()[i].computer_id == -1:
            assigned_values.append("None")
        else:
            assigned_values.append(users.query.all()[i].computer_id)
    for i in range(0, len(computer.query.all())):
        computer_client_id.append(computer.query.all()[i].id)
        computers_mac.append(computer.query.all()[i].mac_address)
    return users_username, computer_client_id, assigned_values, levels, assigned_level_2_allowed_to_view


@app.route("/admin-panel", methods=['GET', 'POST'])
@login_required
def admin_panel():
    '''
    The following function simply return the page with the details about each user.
    '''
    if request.method == "POST":
        return redirect("/admin-panel/data", code=307)
    if request.method == 'GET':
        if current_user.level == 3:
            users_username, computer_client_id, assigned_values, levels, assigned_level_2_allowed_to_view = get_admin_panel_data()
            return render_template("admin_panel.html", users_username = users_username, computer_client_id=computer_client_id, assigned_values=assigned_values, levels=levels,assigned_level_2_allowed_to_view=assigned_level_2_allowed_to_view, computer_list_nev =computer_client_id, level_nev = int(current_user.level),zip=itertools.zip_longest)
        else:
            return redirect('/')



def level_2_handle(remove_vals, user,level):
    '''
    The function handles the LV 2 output that it recieved from the client.
    '''

    count = 0
    if level == 2:
        if remove_vals[0] == "None":
            print("Allowed to view: " + "None")
            users.query.filter_by(username = user).update(dict(allow_to_view_level_2 = "None"))
            db.session.add(users)
            db.session.commit()
        try:
            print("trying level 2")
            allow_to_view = ""
            for i in remove_vals:
                count = count + 1
                i = int(i) # checking if it only contains digits
                i = str(i)
                if count != len(remove_vals):
                    allow_to_view = allow_to_view + i + ","
                else:
                    allow_to_view = allow_to_view + i
            print("Allowed to view: " + allow_to_view)
            users.query.filter_by(username = user).update(dict(allow_to_view_level_2 = allow_to_view))
            db.session.add(users)
            db.session.commit()
        except:
            print("err level 2")
            return "None"
    else:
        print("err2")
        return "None"


@app.route("/admin-panel/data", methods=['POST'])
@login_required
def admin_data():
    '''
    The following function handles the request that the admin sent and updates everything accordingly.
    '''

    if request.method == "POST":
        try:
            assign_value = -1
            user = ""
            remove_vals = []
            print(request.get_data())
            data = request.get_data().decode()
            try:
                remove_vals = data.split('&')[2]
            except:
                remove_vals = "None"
            try:
                user = data.split("=")[0]
                assign_value = data.split("=")[1]
                assign_value = assign_value.split("&")[0]
                level = data.split('&')[1]
            except:
                return {"Values" : "failed"}
            print(user)
            print(assign_value)
            print(level)
            print(remove_vals)
            if assign_value == "None":
                assign_value = -1
            try:
                assign_value = int(assign_value)
                user = str(user)
                level = int(level)
            except:
                return {"Values" : "failed"}
            user_found = False
            username_pos = -1
            for i in range(0,len(users.query.all())):
                if user ==  users.query.all()[i].username:
                    username_pos = i
            if assign_value != -1:
                for j in range(0,len(users.query.all())):
                    print("user: ", end="")
                    print(users.query.all()[j].username)
                    if user == users.query.all()[j].username:
                        user_found = True
                        print("found")
                    if assign_value == users.query.all()[j].computer_id and j != username_pos:
                        print("Failed")
                        return {"Values" : "failed"}
            if (user_found == False and assign_value != -1) or level > 3:
                print("the err2 ")
                return {"Values" : "failed"}
            print("passed!")
            users.query.filter_by(username = user).update(dict(computer_id = assign_value, level=level, allow_to_view_level_2= remove_vals))
            db.session.commit()
            print("almost there")
            if assign_value == -1:
                assign_value = "None"
            return {"computer id" : assign_value, "computer level": level, "level 2" : remove_vals}
        except:
            print("the err")
            return {"Values" : "failed"}

@app.route("/")
@login_required
def index():
    all_computers = []
    for i in range(0, len(computer.query.all())):
        all_computers.append(computer.query.all()[i].id)
    return render_template("index.html", user=current_user.username,level =int(current_user.level), computer_list_nev=all_computers)

''' Client '''

file_cl = "" # The frame that the client sends.
pos_foramt = {} # the X & Y position of the mouse on the img with the ID
lock_foramt = {} # Variable that indicates on wether to lock the screen or not with the ID.
client_id = {}

@app.route('/computers/<int:id>')
@login_required
def root(id):
    if current_user.is_authenticated:
        if current_user.level == 1:
            if current_user.computer_id == id:
                return render_template('computer.html')
        elif current_user.level == 2:
            if current_user.computer_id == id:
                return render_template('computer.html')
            try:
                allow_to_acces = current_user.allow_to_view_level_2.split(',')
            except:
                allow_to_acces = current_user.allow_to_view_level_2
            if len(allow_to_acces) == 1:
                print("Abort!")
                if allow_to_acces[0] == "None":
                    return abort(404)
                elif int(allow_to_acces[0]) == id:
                    return render_template('computer.html')
        
            else:
                for i in allow_to_acces:
                    i = int(i)
                    if i == id:
                        return render_template('computer.html')
        
        elif current_user.level == 3:
            return render_template('computer.html')
    else:
        return redirect("/login")


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
            formatted_history = formatted_history + "DATE: " + history_tuple[0] + "<br> URL: " + history_tuple[1] + "<br><br>"
            # formatted_history = formatted_history + "Date: " + date + " URL: " + url
    # print(formatted_history)
    socketio.emit("info", {"procs": formatted_procs, "history" : formatted_history}, room=str(id))
    return "200 OK"


@socketio.on("pic click")
def pic_click(data):
    global pos_foramt
    pos_x = data["posX"]
    pos_y = data["posY"]
    id = data["room"]
    pos_foramt = {id: [pos_x, pos_y]}

@socketio.on("lock")
def lock_client(data):
    global lock_foramt
    lock = data["lock"]
    id = data["room"]
    lock_foramt = {id: lock}

"""@app.route("/action", methods=["POST"])
def action():"""

class ClientSocket:
    def __init__(self):
        self.s = socket.socket()         
        print ("Socket successfully created")
        port = 12341
        self.s.bind(('', port))         
        print ("socket binded to %s" %(port))
        self.s.listen(5) # the amount of computers connected

    def accept(self):
        while True:
            c, addr = self.s.accept()
            print ('Got connection from', addr )
            threading.Thread(target=self.client_verification, args=[c], daemon=True).start()
            # multiprocessing.Process(target=send_client, args=("c", )).start()
        
    def client_verification(self, c):
        global pos_foramt
        global lock_foramt
        global client_id
        print("active")
        id = str(c.recv(1024).decode()) # making sure
        client_id[id] = c
        while True:
            if len(pos_foramt) > 0:
                for client_pos in pos_foramt:
                    for client in list(client_id):
                        if client == client_pos:
                            self.send_client(c, pos_foramt, "pos", id)
                            pos_foramt = {} # restting the variables so it wont send it all the time.
            if len(lock_foramt) > 0:
                for client_lock in lock_foramt:
                    for client in list(client_id):
                        if client == client_lock:
                            self.send_client(c, lock_foramt, "lock", id)
                            lock_foramt = {} # restting the variables so it wont send it all the time.


    def send_client(self, c, s_format, identify, id):
        try:
            if identify == "pos":
                position = f'["{s_format[id][0]}", "{s_format[id][1]}"]' # formatting the string as a list
                c.send(position.encode()) # sending data to the client
            else:
                if s_format[id] == "True":
                    c.send("Lock".encode())
                else:
                    c.send("Unlock".encode())
        except socket.error:
            print("Bye!")
            del client_id[id] # in case that the client disconnect.
            print(client_id)

if __name__ == '__main__':
    client_socket = ClientSocket()
    socketio_func = functools.partial(socketio.run, app, host="0.0.0.0")
    threading.Thread(target=socketio_func).start()
    threading.Thread(target=client_socket.accept, daemon=True).start()
    # socketio.run(app, host="0.0.0.0", debug=True)

