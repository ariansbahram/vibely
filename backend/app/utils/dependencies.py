import spotipy

from fastapi import Cookie, HTTPException

from app.services.spotify_auth import get_spotify_oauth
from app.services.token_store import get_token, update_token


def get_spotify_client(vibely_session: str = Cookie(None)):
    token_info = get_token(vibely_session) if vibely_session else None

    if not token_info:
        raise HTTPException(
            status_code=401,
            detail="Not logged in to Spotify.",
        )

    spotify_oauth = get_spotify_oauth()

    if spotify_oauth.is_token_expired(token_info):
        token_info = spotify_oauth.refresh_access_token(token_info["refresh_token"])
        update_token(vibely_session, token_info)

    return spotipy.Spotify(auth=token_info["access_token"])
