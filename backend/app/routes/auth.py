from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from spotipy.oauth2 import SpotifyOauthError

from app.services.spotify_auth import FRONTEND_URL, get_spotify_oauth
from app.services.token_store import create_session

router = APIRouter(
    prefix="/auth",
    tags=["Spotify Authentication"],
)


def back_to_app(result: str) -> RedirectResponse:
    """Send the user back to the frontend, telling it how the login went.

    result is "connected", "denied" (the user said no on Spotify's page), or "error".
    """
    return RedirectResponse(f"{FRONTEND_URL}/?spotify={result}")


@router.get("/login")
def spotify_login():
    spotify_oauth = get_spotify_oauth()
    authorization_url = spotify_oauth.get_authorize_url()
    return RedirectResponse(authorization_url)


@router.get("/callback")
def spotify_callback(code: str = None, error: str = None):
    # Spotify sends the user here after its login page, with either a code or an error
    if error:
        return back_to_app("denied" if error == "access_denied" else "error")

    if not code:
        return back_to_app("error")

    try:
        token_info = get_spotify_oauth().get_access_token(code)
    except SpotifyOauthError:
        return back_to_app("error")  # e.g. the code expired or was already used

    session_id = create_session(token_info)

    response = back_to_app("connected")
    response.set_cookie(
        key="vibely_session",
        value=session_id,
        httponly=True,              # JavaScript can't read it, which protects it from theft
        samesite="lax",             # only sent from your own site's pages
        max_age=60 * 60 * 24 * 7,   # browser keeps it for 7 days
    )
    return response
