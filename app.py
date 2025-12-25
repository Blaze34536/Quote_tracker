from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template("rfqEditor2.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signin():
    return render_template("signup.html")

@app.route("/logout")
def logout():
    return render_template("logout.html")

@app.route("/rfq-list")
def rfqList():
    return render_template("rfqList.html")

# @app.route("/rfq-editor")
# def rfqList():
#     return render_template("rfqEditor.html")