from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from flask_wtf.csrf import CSRFProtect
from src.config import Config
from src.auth.utils import login_required, get_current_user, role_required
from src.SupaClient import get_supabase
from src.api import api

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)
app.register_blueprint(api)
csrf.exempt(api)

@app.route("/rfq-entry")
@role_required("admin", "sales")
def rfq(user):
    return render_template("rfqEditor.html") 

@app.route("/")
@login_required
def index(user):
    return redirect(url_for('rfq_list'))

@app.route("/login")
def login():
    user = get_current_user()
    if user:
        return redirect(url_for('rfq'))
    return render_template("login.html")

@app.route("/make-user")
@role_required("admin")
def make_user(user):
    return render_template("makeUser.html")

@app.route("/admin")
@role_required("admin")
def admin(user):
    return render_template("admin.html")

@app.route("/report")
@role_required("admin")
def report(user):
    return render_template("report.html")

@app.route("/logout")
@login_required
def logout(user):
    supabase = get_supabase()
    supabase.auth.sign_out()
    
    response = make_response(redirect(url_for('login')))
    response.set_cookie('access_token', '', expires=0)
    response.set_cookie('csrf_token', '', expires=0)
    return response

@app.route("/rfq-list")
@login_required
def rfq_list(user):
    return render_template("rfqList.html", user=user)

if __name__ == "__main__":
    app.run(debug=True)
