from flask import Flask, render_template, redirect, request, jsonify, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
import spotipy
from spotipy.exceptions import SpotifyException
import requests
import logging
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)

app.config["SECRET_KEY"] = "super secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = "False"
app.config["WTF_CSRF_ENABLED"] = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('spotify_party.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        username = request.form["username"]
        if username == "ALL":
            clear_users()
        else:
            user_to_delete = User.query.filter_by(username=username).first()
            if user_to_delete:
                db.session.delete(user_to_delete)
                try:
                    db.session.commit()
                    logger.info(f"User '{username}' logged out successfully")
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.error(f"Failed to log out user '{username}': {str(e)}")
                    return "Couldn't log out", 409
            else:
                logger.warning(f"Attempted to log out non-existent user: {username}")
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

    if not code:
        logger.error("No authorization code received in callback")
        return redirect("/")

    if "username" not in session:
        logger.error("No username in session during callback")
        return redirect("/")

    auth_token_url = f"{API_BASE}/api/token"
    try:
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
        res.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to obtain access token from Spotify: {str(e)}")
        return redirect("/")

    token_data = res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        logger.error(f"No access token in Spotify response: {token_data}")
        return redirect("/")

    username = session["username"]
    new_user = User(username=username, token=access_token)
    db.session.add(new_user)

    try:
        db.session.commit()
        logger.info(f"User '{username}' authenticated successfully")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Failed to save user '{username}' to database: {str(e)}")
        return redirect("/")

    return redirect("/")


@app.route("/", methods=["GET", "POST"])
def party():
    form = SongForm()
    if form.is_submitted():
        play()
        return redirect(url_for("party"))

    url = "/static/images/default.png"
    item = "Nothing is Playing"
    playback = None

    users = User.query.all()
    if len(users) > 0:
        sp = spotipy.Spotify(auth=users[0].token)

        try:
            playback = sp.current_playback()
        except SpotifyException as e:
            if e.http_status == 401:
                # Token expired or invalid - clear users
                logger.warning(f"Invalid/expired token for user, clearing users: {str(e)}")
                clear_users()
            else:
                logger.error(f"Spotify API error in party(): {str(e)}")
        except Exception as e:
            # Unexpected error, log it but don't clear users
            logger.error(f"Unexpected error fetching playback in party(): {str(e)}")

    if playback is not None:
        try:
            url = playback["item"]["album"]["images"][0]["url"]
            item = playback["item"]["name"] + " - " + playback["item"]["artists"][0]["name"]
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing playback data: {str(e)}")

    return render_template("party.html", form=form, item=item, url=url)


@app.route("/users", methods=["GET", "POST"])
def users():
    playback = []
    spotipy_objects = []
    users = []
    listeners = []
    has_auth_error = False

    for user in User.query.all():
        users.append(user)
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    for idx, sp in enumerate(spotipy_objects):
        try:
            current_playback = sp.current_playback()
            playback.append(current_playback)
        except SpotifyException as e:
            if e.http_status == 401:
                # Token expired or invalid
                logger.warning(f"Invalid/expired token for user {users[idx].username}: {str(e)}")
                has_auth_error = True
            else:
                logger.error(f"Spotify API error for user {users[idx].username}: {str(e)}")
                playback.append(None)
        except Exception as e:
            logger.error(f"Unexpected error fetching playback for user {users[idx].username}: {str(e)}")
            playback.append(None)

    # Only clear users if there was an auth error
    if has_auth_error:
        clear_users()
        return redirect("/")

    for dict_item in playback:
        if dict_item is not None:
            try:
                device_name = dict_item["device"]["name"]
                item_name = dict_item["item"]["name"]
                listener_info = f"{device_name} - {item_name}"
                if listener_info not in listeners:
                    listeners.append(listener_info)
            except (KeyError, TypeError) as e:
                logger.error(f"Error parsing playback data in users(): {str(e)}")

    return render_template("users.html", users=users, listeners=listeners)


@app.route("/play", methods=["POST"])
def play():
    spotipy_objects = []
    users_list = User.query.all()

    if len(users_list) == 0:
        logger.warning("Play request with no authenticated users")
        return "No authenticated users found", 409

    for user in users_list:
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    song_query = request.form.get("song")
    if not song_query:
        logger.warning("Play request with no song specified")
        return "No song specified", 400

    # Search for the song
    try:
        results = spotipy_objects[0].search(song_query, 10, 0, type="track")
        if not results.get("tracks", {}).get("items"):
            logger.info(f"No results found for song query: {song_query}")
            return "No results found for that song", 404
        uri = results["tracks"]["items"][0]["uri"]
        logger.info(f"Playing song: {song_query} (URI: {uri})")
    except SpotifyException as e:
        logger.error(f"Spotify API error searching for song '{song_query}': {str(e)}")
        return f"Error searching for song: {str(e)}", 500
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing search results for '{song_query}': {str(e)}")
        return "Error processing search results", 500

    # Start playback for all users
    playback_errors = []
    for idx, sp in enumerate(spotipy_objects):
        try:
            sp.start_playback(uris=[uri])
        except SpotifyException as e:
            username = users_list[idx].username
            if e.http_status == 404:
                logger.warning(f"No active device for user {username}")
                playback_errors.append(f"No active device for {username}")
            else:
                logger.error(f"Spotify API error starting playback for {username}: {str(e)}")
                playback_errors.append(f"Error for {username}: {str(e)}")
        except Exception as e:
            username = users_list[idx].username
            logger.error(f"Unexpected error starting playback for {username}: {str(e)}")
            playback_errors.append(f"Unexpected error for {username}")

    if playback_errors:
        error_msg = "; ".join(playback_errors)
        return f"Playback errors: {error_msg}", 409

    return "OK", 200


@app.route("/surprise", methods=["POST"])
def surprise():
    spotipy_objects = []
    users_list = User.query.all()

    if len(users_list) == 0:
        logger.warning("Surprise request with no authenticated users")
        return "No authenticated users found", 409

    for user in users_list:
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    surprise_errors = []
    for idx, sp in enumerate(spotipy_objects):
        username = users_list[idx].username
        try:
            sp.shuffle(state=True)
            logger.info(f"Enabled shuffle for user {username}")
        except SpotifyException as e:
            if e.http_status == 404:
                logger.warning(f"No active device for user {username} when enabling shuffle")
                surprise_errors.append(f"No active device for {username}")
                continue
            else:
                logger.error(f"Error enabling shuffle for {username}: {str(e)}")
                surprise_errors.append(f"Shuffle error for {username}")
                continue
        except Exception as e:
            logger.error(f"Unexpected error enabling shuffle for {username}: {str(e)}")
            surprise_errors.append(f"Unexpected error for {username}")
            continue

        try:
            sp.start_playback(context_uri="spotify:playlist:37i9dQZEVXbLRQDuF5jeBp")
            logger.info(f"Started surprise playlist for user {username}")
        except SpotifyException as e:
            if e.http_status == 404:
                logger.warning(f"No active device for user {username} when starting playlist")
                surprise_errors.append(f"No active device for {username}")
            else:
                logger.error(f"Error starting playlist for {username}: {str(e)}")
                surprise_errors.append(f"Playlist error for {username}")
        except Exception as e:
            logger.error(f"Unexpected error starting playlist for {username}: {str(e)}")
            surprise_errors.append(f"Unexpected error for {username}")

    if surprise_errors:
        error_msg = "; ".join(surprise_errors)
        logger.warning(f"Surprise completed with errors: {error_msg}")
        return f"Surprise errors: {error_msg}", 409

    return redirect("/")


@app.route("/toggle_playback", methods=["POST"])
def toggle():
    spotipy_objects = []
    users_list = User.query.all()

    if len(users_list) == 0:
        logger.warning("Toggle playback request with no authenticated users")
        return redirect("/")

    for user in users_list:
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    toggle_errors = []
    for idx, sp in enumerate(spotipy_objects):
        username = users_list[idx].username
        try:
            playback = sp.current_playback()
            if playback is None:
                logger.warning(f"No playback state for user {username}")
                continue

            is_playing = playback.get("is_playing", False)
            if is_playing:
                sp.pause_playback()
                logger.info(f"Paused playback for user {username}")
            else:
                sp.start_playback()
                logger.info(f"Started playback for user {username}")
        except SpotifyException as e:
            if e.http_status == 404:
                logger.warning(f"No active device for user {username} during toggle")
            else:
                logger.error(f"Spotify API error toggling playback for {username}: {str(e)}")
                toggle_errors.append(username)
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing playback state for {username}: {str(e)}")
            toggle_errors.append(username)
        except Exception as e:
            logger.error(f"Unexpected error toggling playback for {username}: {str(e)}")
            toggle_errors.append(username)

    if toggle_errors:
        logger.warning(f"Toggle completed with errors for users: {', '.join(toggle_errors)}")

    return redirect("/")


@app.route("/currently_playing")
def currently_playing():
    playback = []
    spotipy_objects = []
    users_list = User.query.all()

    for user in users_list:
        spotipy_objects.append(spotipy.Spotify(auth=user.token))

    for idx, sp in enumerate(spotipy_objects):
        try:
            current = sp.current_playback()
            playback.append(current)
        except SpotifyException as e:
            logger.error(f"Spotify API error fetching playback for {users_list[idx].username}: {str(e)}")
            playback.append(None)
        except Exception as e:
            logger.error(f"Unexpected error fetching playback for {users_list[idx].username}: {str(e)}")
            playback.append(None)

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
    users_list = User.query.all()
    user_count = len(users_list)

    if user_count == 0:
        logger.info("Clear users called but no users to clear")
        return redirect("/")

    for user in users_list:
        db.session.delete(user)

    try:
        db.session.commit()
        logger.info(f"Successfully cleared {user_count} user(s)")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Failed to clear users: {str(e)}")

    return redirect("/")


if __name__ == "__main__":
    db.create_all()
    app.run(host="127.0.0.1", port=8000, debug=True)
