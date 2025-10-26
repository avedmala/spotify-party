import pytest
from unittest.mock import patch, MagicMock
from flask_app import db, User


class TestParty:
    """Tests for the main party page."""

    def test_party_get_no_users(self, client):
        """Test party page with no users logged in."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Nothing is Playing' in response.data

    @patch('flask_app.spotipy.Spotify')
    def test_party_get_with_user_and_playback(self, mock_spotify, client, test_app, sample_user, mock_spotify_playback):
        """Test party page with active user and playback."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = mock_spotify_playback
        mock_spotify.return_value = mock_sp_instance

        response = client.get('/')
        assert response.status_code == 200
        assert b'Test Song' in response.data
        assert b'Test Artist' in response.data

    @patch('flask_app.spotipy.Spotify')
    def test_party_get_with_user_no_playback(self, mock_spotify, client, test_app, sample_user):
        """Test party page with user but no active playback."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.get('/')
        assert response.status_code == 200
        assert b'Nothing is Playing' in response.data

    @patch('flask_app.spotipy.Spotify')
    def test_party_post_play_song(self, mock_spotify, client, test_app, sample_user, mock_spotify_search_results):
        """Test playing a song from the party page."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = None
        mock_sp_instance.search.return_value = mock_spotify_search_results
        mock_sp_instance.start_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/', data={'song': 'test song'}, follow_redirects=False)
        assert response.status_code == 302
        assert response.location == '/'


class TestPlay:
    """Tests for the play functionality."""

    @patch('flask_app.spotipy.Spotify')
    def test_play_with_users(self, mock_spotify, client, test_app, multiple_users, mock_spotify_search_results):
        """Test playing a song with multiple users."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.search.return_value = mock_spotify_search_results
        mock_sp_instance.start_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/play', data={'song': 'test song'})
        assert response.status_code == 200
        assert response.data == b'OK'

        # Verify start_playback was called for each user
        assert mock_sp_instance.start_playback.call_count == 3

    def test_play_no_users(self, client, test_app):
        """Test playing a song with no users logged in."""
        response = client.post('/play', data={'song': 'test song'})
        assert response.status_code == 409
        assert b'No active device found' in response.data

    @patch('flask_app.spotipy.Spotify')
    def test_play_device_error(self, mock_spotify, client, test_app, sample_user):
        """Test playing when device is not available."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.search.return_value = {
            "tracks": {"items": [{"uri": "spotify:track:test"}]}
        }
        mock_sp_instance.start_playback.side_effect = Exception("No device found")
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/play', data={'song': 'test song'})
        assert response.status_code == 409


class TestSurprise:
    """Tests for the surprise/shuffle functionality."""

    @patch('flask_app.spotipy.Spotify')
    def test_surprise_with_users(self, mock_spotify, client, test_app, multiple_users):
        """Test surprise shuffle with multiple users."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.shuffle.return_value = None
        mock_sp_instance.start_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/surprise', follow_redirects=False)
        assert response.status_code == 302
        assert response.location == '/'

        # Verify shuffle and start_playback were called for each user
        assert mock_sp_instance.shuffle.call_count == 3
        assert mock_sp_instance.start_playback.call_count == 3

    @patch('flask_app.spotipy.Spotify')
    def test_surprise_device_error(self, mock_spotify, client, test_app, sample_user):
        """Test surprise when device error occurs."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.shuffle.side_effect = Exception("No device found")
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/surprise')
        assert response.status_code == 409


class TestTogglePlayback:
    """Tests for the toggle playback functionality."""

    @patch('flask_app.spotipy.Spotify')
    def test_toggle_pause(self, mock_spotify, client, test_app, sample_user):
        """Test toggling from playing to paused."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = {'is_playing': True}
        mock_sp_instance.pause_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/toggle_playback', follow_redirects=False)
        assert response.status_code == 302

        mock_sp_instance.pause_playback.assert_called_once()

    @patch('flask_app.spotipy.Spotify')
    def test_toggle_play(self, mock_spotify, client, test_app, sample_user):
        """Test toggling from paused to playing."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = {'is_playing': False}
        mock_sp_instance.start_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/toggle_playback', follow_redirects=False)
        assert response.status_code == 302

        mock_sp_instance.start_playback.assert_called_once()

    @patch('flask_app.spotipy.Spotify')
    def test_toggle_multiple_users(self, mock_spotify, client, test_app, multiple_users):
        """Test toggle with multiple users."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = {'is_playing': True}
        mock_sp_instance.pause_playback.return_value = None
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/toggle_playback', follow_redirects=False)
        assert response.status_code == 302

        # Should be called once for each user
        assert mock_sp_instance.pause_playback.call_count == 3

    @patch('flask_app.spotipy.Spotify')
    def test_toggle_error_handling(self, mock_spotify, client, test_app, sample_user):
        """Test toggle when an error occurs."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.side_effect = Exception("API error")
        mock_spotify.return_value = mock_sp_instance

        response = client.post('/toggle_playback', follow_redirects=False)
        assert response.status_code == 302
        assert response.location == '/'


class TestUsers:
    """Tests for the users page."""

    def test_users_no_users(self, client):
        """Test users page with no users."""
        response = client.get('/users')
        assert response.status_code == 200

    @patch('flask_app.spotipy.Spotify')
    def test_users_with_playback(self, mock_spotify, client, test_app, multiple_users, mock_spotify_playback):
        """Test users page with active playback."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.return_value = mock_spotify_playback
        mock_spotify.return_value = mock_sp_instance

        response = client.get('/users')
        assert response.status_code == 200
        assert b'user1' in response.data
        assert b'user2' in response.data
        assert b'user3' in response.data

    @patch('flask_app.spotipy.Spotify')
    def test_users_with_error(self, mock_spotify, client, test_app, sample_user):
        """Test users page when Spotify API errors occur."""
        mock_sp_instance = MagicMock()
        mock_sp_instance.current_playback.side_effect = Exception("API error")
        mock_spotify.return_value = mock_sp_instance

        with test_app.app_context():
            response = client.get('/users')
            # Should clear users and still return 200
            assert response.status_code == 200
            # Users should be cleared
            assert User.query.count() == 0
