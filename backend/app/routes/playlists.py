import spotipy

from fastapi import APIRouter, Depends, HTTPException

from app.models.playlist import PlaylistRequest, PlaylistResponse
from app.services.spotify_playlists import create_playlist
from app.utils.dependencies import get_spotify_client

router = APIRouter(
    tags=["Playlists"],
)


@router.post("/playlists", response_model=PlaylistResponse, status_code=201)
def save_playlist(
    request: PlaylistRequest,
    spotify: spotipy.Spotify = Depends(get_spotify_client),  # 401 if not logged in
):
    try:
        return create_playlist(
            spotify,
            request.name,
            request.track_ids,
            description=request.description,
            public=request.public,
        )
    except spotipy.SpotifyException as error:
        if error.http_status == 403:
            # Usually: the login is missing the playlist permissions, or the Spotify app
            # is in Development Mode and this user isn't on its list of allowed users
            raise HTTPException(
                status_code=403,
                detail="Spotify didn't allow creating the playlist. Try logging in again.",
            )

        if error.http_status == 400:
            raise HTTPException(
                status_code=400,
                detail=f"Spotify rejected the playlist: {error.msg}",
            )

        raise HTTPException(
            status_code=502,
            detail="Spotify couldn't create the playlist. Try again in a moment.",
        )
