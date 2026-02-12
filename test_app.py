import unittest
from flask_app import app, db, User

class SpotifyPartyTestCase(unittest.TestCase):
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

    def test_party_page_empty(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Nothing is Playing', response.data)

    def test_party_page_with_user(self):
        with app.app_context():
            user = User(username='testuser', token='testtoken')
            db.session.add(user)
            db.session.commit()
        # Note: Spotify API calls will fail, but we're testing the DB logic
        # and the route's resilience.
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_list_users(self):
        with app.app_context():
            user = User(username='testuser', token='testtoken')
            db.session.add(user)
            db.session.commit()
        response = self.app.get('/list_users')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'testuser', response.data)

    def test_logout(self):
        with app.app_context():
            user = User(username='testuser', token='testtoken')
            db.session.add(user)
            db.session.commit()

        # Test logout specific user
        response = self.app.post('/logout', data={'username': 'testuser'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertIsNone(User.query.filter_by(username='testuser').first())

    def test_clear_users(self):
        with app.app_context():
            user = User(username='testuser', token='testtoken')
            db.session.add(user)
            db.session.commit()

        response = self.app.get('/clear_users', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertEqual(User.query.count(), 0)

if __name__ == '__main__':
    unittest.main()
