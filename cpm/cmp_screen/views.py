from flask import Blueprint, request, render_template, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
#from cmp_screen.api import recv_img
cmp_screen = Blueprint("cmp_screen" , __name__)
login_manager = LoginManager()
login_manager.init_app(cmp_screen)

@cmp_screen.route("/")
def index():
    if request.method == "GET":
        return render_template("screen.html")

@cmp_screen.route("/recv-sc", methods=["GET", "POST"])
def recv_sc():
    return render_template("screen.html")

