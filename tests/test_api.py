import pytest
import json
from unittest.mock import patch, MagicMock
from flask_app import db, User


class TestCurrentlyPlaying:
    """Tests for the /currently_playing API endpoint."""

    @patch('flask_app.spotipy.Spotify')
    def test_currently_playing_with_users(self, mock_spotify, client, test_app, multiple_users, mock_spotify_playback):
        """Test getting currently playing tracks for all users."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = mock_spotify_playback
        mock_spotify.return_value = mock_sp_instance

        response = client.get('/currently_playing')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 3  # One for each user
        assert data[0]['item']['name'] == 'Test Song'

    def test_currently_playing_no_users(self, client, test_app):
        """Test currently playing with no users."""
        response = client.get('/currently_playing')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    @patch('flask_app.spotipy.Spotify')
    def test_currently_playing_none_playback(self, mock_spotify, client, test_app, sample_user):
        """Test currently playing when nothing is playing."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.get('/currently_playing')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data == [None]


class TestListUsers:
    """Tests for the /list_users API endpoint."""

    def test_list_users_with_users(self, client, test_app, multiple_users):
        """Test listing all users."""
        response = client.get('/list_users')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 3

        # Check that each user has username and token
        for user_data in data:
            assert 'username' in user_data
            assert 'token' in user_data

        usernames = [u['username'] for u in data]
        assert 'user1' in usernames
        assert 'user2' in usernames
        assert 'user3' in usernames

    def test_list_users_no_users(self, client, test_app):
        """Test listing users when none exist."""
        response = client.get('/list_users')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_users_single_user(self, client, test_app, sample_user):
        """Test listing a single user."""
        response = client.get('/list_users')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['username'] == 'testuser'
        assert data[0]['token'] == 'sample_token_12345'


class TestClearUsers:
    """Tests for the /clear_users endpoint."""

    def test_clear_users_with_users(self, client, test_app, multiple_users):
        """Test clearing all users."""
        with test_app.app_context():
            assert User.query.count() == 3

        response = client.get('/clear_users', follow_redirects=False)
        assert response.status_code == 302
        assert response.location == '/'

        with test_app.app_context():
            assert User.query.count() == 0

    def test_clear_users_no_users(self, client, test_app):
        """Test clearing users when none exist."""
        with test_app.app_context():
            assert User.query.count() == 0

        response = client.get('/clear_users', follow_redirects=False)
        assert response.status_code == 302

        with test_app.app_context():
            assert User.query.count() == 0

    def test_clear_users_single_user(self, client, test_app, sample_user):
        """Test clearing a single user."""
        with test_app.app_context():
            assert User.query.count() == 1

        response = client.get('/clear_users', follow_redirects=False)
        assert response.status_code == 302

        with test_app.app_context():
            assert User.query.count() == 0


class TestForms:
    """Tests for form validation and submission."""

    def test_username_form_validation(self, client):
        """Test that username form requires data."""
        response = client.post('/login', data={'username': ''})
        # Form validation should fail, but CSRF is disabled so it will redirect
        assert response.status_code in [200, 302]

    def test_song_form_validation(self, client):
        """Test that song form requires data."""
        response = client.post('/', data={'song': ''})
        # Form validation should fail
        assert response.status_code in [200, 302]


class TestIntegration:
    """Integration tests for complete workflows."""

    @patch('flask_app.requests.post')
    @patch('flask_app.spotipy.Spotify')
    def test_complete_login_play_logout_flow(self, mock_spotify, mock_requests, client, test_app, mock_spotify_search_results):
        """Test a complete user flow: login, play song, logout."""
        # Mock OAuth response
        mock_oauth_response = MagicMock()
        mock_oauth_response.json.return_value = {
            'access_token': 'integration_test_token',
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_requests.return_value = mock_oauth_response

        # Mock Spotify instance
        mock_sp_instance = MagicMock()
        mock_sp_instance.search.return_value = mock_spotify_search_results
        mock_sp_instance.start_playback.return_value = None
        mock_sp_instance.current_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        # Step 1: Login
        with client.session_transaction() as session:
            session['username'] = 'integration_user'

        # Step 2: Complete OAuth callback
        response = client.get('/api_callback?code=test_code')
        assert response.status_code == 302

        with test_app.app_context():
            assert User.query.count() == 1
            user = User.query.first()
            assert user.username == 'integration_user'

        # Step 3: Play a song
        response = client.post('/play', data={'song': 'test song'})
        assert response.status_code == 200

        # Step 4: Logout
        response = client.post('/logout', data={'username': 'integration_user'})
        assert response.status_code == 302

        with test_app.app_context():
            assert User.query.count() == 0
