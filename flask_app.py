from flask import Flask, render_template, redirect, request, jsonify, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
import spotipy
from spotipy.client import SpotifyException
import requests
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

app.config["SECRET_KEY"] = "super secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = "False"
app.config["WTF_CSRF_ENABLED"] = False

db = SQLAlchemy(app)


class UsernameForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log In")


class SongForm(FlaskForm):
    song = StringField("Song", validators=[DataRequired()])


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default="default.png")
    token = db.Column(db.String(500), nullable=False, unique=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.token}')"


CLI_ID = "335bf2abece14ce0b1924fa43a7371fc"
CLI_SEC = "6638b23346cb4a05a3a88e14f20510c3"
API_BASE = "https://accounts.spotify.com"
REDIRECT_URI = "http://127.0.0.1:8000/api_callback"
SCOPE = "user-read-playback-state,user-modify-playback-state"
# Set this to True for testing but you probably want it set to False in production.
SHOW_DIALOG = False


@app.route("/login", methods=["GET", "POST"])
def login():
    form = UsernameForm()
    if form.is_submitted():
        session["username"] = request.form["username"]
        return redirect("auth")
    else:
        return render_template("login.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    form = UsernameForm()
    if form.is_submitted():
        if request.form["username"] == "ALL":
            clear_users()
        else:
            user = User.query.filter_by(username=request.form["username"]).first()
            if user:
                db.session.delete(user)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    return "Couldn't log out", 409
    else:
        return render_template("logout.html", form=form)

    return redirect("/")


@app.route("/auth")
def auth():
    auth_url = f"{API_BASE}/authorize?client_id={CLI_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&show_dialog={SHOW_DIALOG}"
    return redirect(auth_url)


@app.route("/api_callback")
def api_callback():
    code = request.args.get("code")

    auth_token_url = f"{API_BASE}/api/token"
    res = requests.post(
        auth_token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLI_ID,
            "client_secret": CLI_SEC,
        },
    )

    res_json = res.json()
    access_token = res_json.get("access_token")

    if not access_token:
        return "Failed to retrieve access token.", 400

    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=username).first()

    if user:
        user.token = access_token
    else:
        user = User(username=username, token=access_token)
        db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return "Failed to save user information.", 500

    return redirect("/")


@app.route("/", methods=["GET", "POST"])
def party():
    form = SongForm()
    if form.is_submitted():
        play()
        return redirect(url_for("party"))

    url = "/static/images/default.png"
    item = "Nothing is Playing"

    users = User.query.all()
    if not users:
        return render_template("party.html", form=form, item=item, url=url)

    sp = spotipy.Spotify(auth=users[0].token)

    playback = None
    try:
        playback = sp.current_playback()
    except SpotifyException:
        return redirect(url_for("logout"))

    if playback and playback.get("item"):
        url = playback["item"]["album"]["images"][0]["url"]
        item = playback["item"]["name"] + " - " + playback["item"]["artists"][0]["name"]

    return render_template("party.html", form=form, item=item, url=url)


@app.route("/users", methods=["GET", "POST"])
def users():
    playback = []
    spotipy_objects = []
    users = []
    listeners = []

    for user in User.query.all():
        users.append(user)
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    for sp in spotipy_objects:
        try:
            current = sp.current_playback()
            if current:
                playback.append(current)
        except SpotifyException:
            # Token might be expired, log out the user
            return redirect(url_for("logout"))

    for dict_item in playback:
        if dict_item.get("device") and dict_item.get("item"):
            item = (
                dict_item["device"]["name"]
                + " - "
                + dict_item["item"]["name"]
            )
            if item not in listeners:
                listeners.append(item)

    return render_template("users.html", users=users, listeners=listeners)


@app.route("/play", methods=["POST"])
def play():
    spotipy_objects = []

    for user in User.query.all():
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    if not spotipy_objects:
        return "No active device found", 409

    try:
        results = spotipy_objects[0].search(request.form["song"], 10, 0, type="track")
        if not results["tracks"]["items"]:
            return "Song not found", 404
        uri = results["tracks"]["items"][0]["uri"]
    except SpotifyException:
        return "Could not perform search", 500

    for sp in spotipy_objects:
        try:
            sp.start_playback(uris=[uri])
        except SpotifyException:
            return "No active device found", 409

    return "OK", 200


@app.route("/surprise", methods=["POST"])
def surprise():
    spotipy_objects = []

    for user in User.query.all():
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    for sp in spotipy_objects:
        try:
            sp.shuffle(state=True)
            sp.start_playback(context_uri="spotify:playlist:37i9dQZEVXbLRQDuF5jeBp")
        except SpotifyException:
            return "No active device found", 409

    return redirect("/")


@app.route("/toggle_playback", methods=["POST"])
def toggle():
    spotipy_objects = []

    for user in User.query.all():
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    for sp in spotipy_objects:
        try:
            playback = sp.current_playback()
            if playback and playback.get("is_playing"):
                sp.pause_playback()
            else:
                sp.start_playback()
        except SpotifyException:
            return redirect("/")

    return redirect("/")


@app.route("/currently_playing")
def currently_playing():
    playback = []
    spotipy_objects = []

    for user in User.query.all():
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    for sp in spotipy_objects:
        try:
            current = sp.current_playback()
            if current:
                playback.append(current)
        except SpotifyException:
            # Ignore users with expired tokens
            pass

    return jsonify(playback)


@app.route("/list_users")
def list_users():
    users = []

    for user in User.query.all():
        new_data = {"username": user.username, "token": user.token}
        users.append(new_data)

    return jsonify(users)


@app.route("/clear_users")
def clear_users():
    try:
        num_rows_deleted = db.session.query(User).delete()
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

    return redirect("/")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=8000, debug=True)
