import spotipy

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.services.spotify_auth import get_spotify_oauth

router = APIRouter(
    prefix="/auth",
    tags=["Spotify Authentication"],
)


@router.get("/login")
def spotify_login():
    spotify_oauth = get_spotify_oauth()
    authorization_url = spotify_oauth.get_authorize_url()
    return RedirectResponse(authorization_url)


@router.get("/callback")
def spotify_callback(code: str = None, error: str = None):
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"Spotify authorization failed: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="Spotify did not return an authorization code.",
        )

    spotify_oauth = get_spotify_oauth()
    token_info = spotify_oauth.get_access_token(code)

    spotify = spotipy.Spotify(auth=token_info["access_token"])
    user = spotify.current_user()

    return {
        "message": "Spotify authentication successful",
        "user": {
            "id": user["id"],
            "display_name": user.get("display_name"),
            "email": user.get("email"),
        },
    }
