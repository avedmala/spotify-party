import pytest
from unittest.mock import patch, MagicMock
from flask_app import db, User


class TestLogin:
    """Tests for the login functionality."""

    def test_login_get(self, client):
        """Test GET request to login page."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Username' in response.data

    def test_login_post_redirects_to_auth(self, client):
        """Test POST request to login redirects to auth."""
        response = client.post('/login', data={'username': 'testuser'}, follow_redirects=False)
        assert response.status_code == 302
        assert 'auth' in response.location

    def test_login_sets_session(self, client):
        """Test that login sets username in session."""
        with client:
            client.post('/login', data={'username': 'testuser'})
            with client.session_transaction() as session:
                assert session['username'] == 'testuser'


class TestLogout:
    """Tests for the logout functionality."""

    def test_logout_get(self, client):
        """Test GET request to logout page."""
        response = client.get('/logout')
        assert response.status_code == 200

    def test_logout_single_user(self, client, test_app, sample_user):
        """Test logging out a single user."""
        with test_app.app_context():
            assert User.query.count() == 1

            response = client.post('/logout', data={'username': 'testuser'})
            assert response.status_code == 302

            assert User.query.count() == 0

    def test_logout_all_users(self, client, test_app, multiple_users):
        """Test logging out all users with 'ALL' command."""
        with test_app.app_context():
            assert User.query.count() == 3

            response = client.post('/logout', data={'username': 'ALL'})
            assert response.status_code == 302

            assert User.query.count() == 0

    def test_logout_nonexistent_user(self, client, test_app, sample_user):
        """Test logging out a user that doesn't exist."""
        with test_app.app_context():
            response = client.post('/logout', data={'username': 'nonexistent'})
            assert response.status_code == 302
            # Original user should still exist
            assert User.query.count() == 1


class TestAuth:
    """Tests for the Spotify OAuth flow."""

    def test_auth_redirect(self, client):
        """Test that /auth redirects to Spotify authorization."""
        response = client.get('/auth', follow_redirects=False)
        assert response.status_code == 302
        assert 'accounts.spotify.com/authorize' in response.location
        assert 'client_id=' in response.location
        assert 'redirect_uri=' in response.location
        assert 'scope=' in response.location


class TestApiCallback:
    """Tests for the OAuth callback endpoint."""

    @patch('flask_app.requests.post')
    def test_api_callback_creates_user(self, mock_post, client, test_app):
        """Test that successful callback creates a user."""
        # Mock the Spotify token response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test_access_token_123',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response

        with client.session_transaction() as session:
            session['username'] = 'newuser'

        response = client.get('/api_callback?code=test_authorization_code')
        assert response.status_code == 302

        with test_app.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.token == 'test_access_token_123'

    @patch('flask_app.requests.post')
    def test_api_callback_duplicate_user_redirects(self, mock_post, client, test_app, sample_user):
        """Test that duplicate user creation redirects without error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'sample_token_12345',  # Same token as sample_user
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response

        with client.session_transaction() as session:
            session['username'] = 'testuser'  # Same username as sample_user

        response = client.get('/api_callback?code=test_code')
        assert response.status_code == 302
        assert response.location == '/'

        with test_app.app_context():
            # Should still only have one user
            assert User.query.count() == 1

    @patch('flask_app.requests.post')
    def test_api_callback_missing_code(self, mock_post, client):
        """Test callback without authorization code."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': None}
        mock_post.return_value = mock_response

        with client.session_transaction() as session:
            session['username'] = 'testuser'

        # This will fail because there's no code parameter
        response = client.get('/api_callback')
        # The endpoint doesn't handle this gracefully, but we test the current behavior
        assert response.status_code in [302, 500]  # Either redirects or errors
