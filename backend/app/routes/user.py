import spotipy

from fastapi import APIRouter, Depends

from app.services.spotify_user import get_user_profile
from app.utils.dependencies import get_spotify_client

router = APIRouter(
    tags=["Spotify User"],
)


@router.get("/me")
def read_current_user(spotify: spotipy.Spotify = Depends(get_spotify_client)):
    return get_user_profile(spotify)
