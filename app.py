import os
import pathlib
import requests
from flask import Flask, session, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from pymongo import MongoClient


app = Flask(__name__)
app.secret_key = "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"

#mongodb connection
client = MongoClient("mongodb+srv://jones:jones@cluster0.qkysz.mongodb.net/")
db = client["ganesha_jumbo_idly"]
collection = db["users"]


os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = "/home/tf/jumbo idly/auth/client_secrets.json"  # Update this with the correct file path
GOOGLE_CLIENT_ID = "93528188143-vipv83t9k9po3she6ev6ji23gc55bqbm.apps.googleusercontent.com"
REDIRECT_URI = "http://localhost:5000/callback"

flow = Flow.from_client_secrets_file(
    client_secrets_file=CLIENT_SECRETS_FILE,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri=REDIRECT_URI
)

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function(*args, **kwargs)
    return wrapper

@app.route("/login")
def login():
    session.clear()
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(code=request.args.get("code"))

    if session.get("state") != request.args.get("state"):
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    token_request = google.auth.transport.requests.Request(session=request_session)

    try:
        id_info = id_token.verify_oauth2_token(
            id_token=credentials.id_token,  # Updated this line
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
    except ValueError as e:
        print(f"Error verifying ID token: {str(e)}")
        abort(500)  # Invalid ID token

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")

    # Check if user is already registered
    existing_user = collection.find_one({"google_id": session["google_id"]})
    if existing_user:
        return "This user already registered."

    # Register user data in the MongoDB database
    user_data = {
        "google_id": session["google_id"],
        "name": session["name"],
        "profile_photo": id_info.get("picture"),
        "email": id_info.get("email"),
        "phone_number": id_info.get("phone_number")
    }
    collection.insert_one(user_data)

    return f"Registration successful. Hello {session['name']}! <br/> <a href='/protected_area'><button>Proceed to Protected Area</button></a>"



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/")
def index():
    return "Hello World <a href='/login'><button>register</button></a>"

@app.route("/protected_area")
@login_is_required
def protected_area():
    return f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
