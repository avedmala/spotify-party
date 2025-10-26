import pytest
import sys
import os

# Add parent directory to path to import flask_app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask_app import app, db, User


@pytest.fixture
def test_app():
    """Create and configure a test application instance."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create a test client for the app."""
    return test_app.test_client()


@pytest.fixture
def runner(test_app):
    """Create a test CLI runner."""
    return test_app.test_cli_runner()


@pytest.fixture
def sample_user(test_app):
    """Create a sample user for testing."""
    with test_app.app_context():
        user = User(
            username='testuser',
            token='sample_token_12345'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def multiple_users(test_app):
    """Create multiple users for testing."""
    with test_app.app_context():
        users = [
            User(username='user1', token='token1'),
            User(username='user2', token='token2'),
            User(username='user3', token='token3')
        ]
        for user in users:
            db.session.add(user)
        db.session.commit()
        return users


@pytest.fixture
def mock_spotify_playback():
    """Mock Spotify playback data."""
    return {
        "device": {
            "name": "Test Device"
        },
        "is_playing": True,
        "item": {
            "name": "Test Song",
            "uri": "spotify:track:test123",
            "album": {
                "images": [
                    {"url": "https://example.com/image.jpg"}
                ]
            },
            "artists": [
                {"name": "Test Artist"}
            ]
        }
    }


@pytest.fixture
def mock_spotify_search_results():
    """Mock Spotify search results."""
    return {
        "tracks": {
            "items": [
                {
                    "uri": "spotify:track:test123",
                    "name": "Test Song",
                    "artists": [{"name": "Test Artist"}]
                }
            ]
        }
    }
