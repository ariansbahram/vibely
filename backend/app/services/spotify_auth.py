import os

from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

SCOPES = [
    "user-read-private",
    "user-read-email",
    "playlist-modify-private",
    "playlist-modify-public",
]


def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=" ".join(SCOPES),
        show_dialog=True,
    )
