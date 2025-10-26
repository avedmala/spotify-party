import pytest
from flask_app import db, User


class TestUserModel:
    """Tests for the User database model."""

    def test_user_creation(self, test_app):
        """Test creating a new user."""
        with test_app.app_context():
            user = User(username='newuser', token='token123')
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == 'newuser'
            assert user.token == 'token123'
            assert user.image_file == 'default.png'

    def test_user_repr(self, test_app, sample_user):
        """Test user representation string."""
        with test_app.app_context():
            user = User.query.first()
            assert repr(user) == f"User('{user.username}', '{user.token}')"

    def test_user_unique_username(self, test_app, sample_user):
        """Test that usernames must be unique."""
        with test_app.app_context():
            duplicate_user = User(username='testuser', token='different_token')
            db.session.add(duplicate_user)

            with pytest.raises(Exception):
                db.session.commit()

    def test_user_unique_token(self, test_app, sample_user):
        """Test that tokens must be unique."""
        with test_app.app_context():
            duplicate_token_user = User(username='different_user', token='sample_token_12345')
            db.session.add(duplicate_token_user)

            with pytest.raises(Exception):
                db.session.commit()

    def test_user_query_all(self, test_app, multiple_users):
        """Test querying all users."""
        with test_app.app_context():
            users = User.query.all()
            assert len(users) == 3
            assert users[0].username == 'user1'
            assert users[1].username == 'user2'
            assert users[2].username == 'user3'

    def test_user_deletion(self, test_app, sample_user):
        """Test deleting a user."""
        with test_app.app_context():
            user = User.query.first()
            db.session.delete(user)
            db.session.commit()

            assert User.query.count() == 0

    def test_user_default_image(self, test_app):
        """Test that default image is set correctly."""
        with test_app.app_context():
            user = User(username='imagetest', token='token456')
            db.session.add(user)
            db.session.commit()

            assert user.image_file == 'default.png'
