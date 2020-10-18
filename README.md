# Spotify Party

## Instructions to use
- **Note:** Must have Spotify Premium
1. [Login](https://mrswagbhinav.pythonanywhere.com/login) with your Spotify username.
2. Your name should appear [here](https://mrswagbhinav.pythonanywhere.com/users).
3. Start playing a song on Spotify so the website can find that device.
4. The name of the device should also now [appear](https://mrswagbhinav.pythonanywhere.com/users).
5. Click the album artwork to pause/play the music.
6. [Logout](https://mrswagbhinav.pythonanywhere.com/logout) once your done by just entering your username.

## API Information
[API Docs](https://documenter.getpostman.com/view/6820223/TVRkb8Aq)

**GET** Request to https://mrswagbhinav.pythonanywhere.com/list_users will list all the users logged in

**GET** Request to https://mrswagbhinav.pythonanywhere.com/currently_playing will list what all the users are listening to

**POST** Request to https://mrswagbhinav.pythonanywhere.com/play with the body `song='song_title'` will start playing that song for all users logged in

**POST** Request to https://mrswagbhinav.pythonanywhere.com/toggle_playback will pause or play the current song

**POST** Request to https://mrswagbhinav.pythonanywhere.com/logout with the body `username='your_username'` will log that user out of the service
