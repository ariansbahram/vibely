import spotipy
from app.services.token_store import create_session
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse


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

    session_id = create_session(token_info)

    spotify = spotipy.Spotify(auth=token_info["access_token"])
    user = spotify.current_user()

    response = JSONResponse({
        "message": "Spotify authentication successful",
        "user": {
            "id": user["id"],
            "display_name": user.get("display_name"),
            "email": user.get("email"),
        },
    })
    response.set_cookie(
        key="vibely_session",
        value=session_id,
        httponly=True,              # JavaScript can't read it, which protects it from theft
        samesite="lax",             # only sent from your own site's pages
        max_age=60 * 60 * 24 * 7,   # browser keeps it for 7 days
    )
    return response

    
    

