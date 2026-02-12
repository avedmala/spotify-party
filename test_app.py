import unittest
from flask_app import app, db, User

class TestApp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_party_page_accessibility(self):
        response = self.app.get('/')
        html = response.data.decode()
        self.assertIn('alt="Spotify Party Logo"', html)
        self.assertIn('aria-label="Toggle Playback"', html)
        self.assertIn('alt="Album Artwork"', html)
        self.assertIn('<label for="song" class="sr-only">Enter Song</label>', html)
        self.assertIn('Play Song</button>', html)

    def test_login_page_accessibility(self):
        response = self.app.get('/login')
        html = response.data.decode()
        self.assertIn('alt="Spotify Party Logo"', html)
        self.assertIn('<label for="username" class="sr-only">Username</label>', html)
        self.assertIn('Log In</button>', html)

    def test_logout_page_accessibility(self):
        response = self.app.get('/logout')
        html = response.data.decode()
        self.assertIn('alt="Spotify Party Logo"', html)
        self.assertIn('<label for="username" class="sr-only">Username</label>', html)
        self.assertIn('Log Out</button>', html)

if __name__ == '__main__':
    unittest.main()
