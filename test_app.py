import unittest
from unittest.mock import patch, MagicMock
from flask_app import app, db, User

class TestApp(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    @patch("spotipy.Spotify")
    def test_party_page_with_podcast(self, mock_spotify):
        # Simulate a user in the database
        with app.app_context():
            test_user = User(username="testuser", token="test_token")
            db.session.add(test_user)
            db.session.commit()

        # Mock the Spotify API to return a podcast
        mock_spotify_instance = MagicMock()
        mock_spotify.return_value = mock_spotify_instance
        mock_spotify_instance.current_playback.return_value = {
            "currently_playing_type": "episode",
            "item": {
                "name": "Test Podcast Episode",
                "images": [{"url": "http://example.com/podcast.jpg"}],
                "show": {"name": "Test Podcast Show"},
            },
        }

        # Make a request to the party page
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Podcast Episode - Test Podcast Show", response.data)
        self.assertIn(b"http://example.com/podcast.jpg", response.data)

if __name__ == "__main__":
    unittest.main()