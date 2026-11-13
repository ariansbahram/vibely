import spotipy

from fastapi import APIRouter, Depends, HTTPException

from app.models.playlist import (
    PlaylistOrderRequest,
    PlaylistOrderResponse,
    PlaylistRequest,
    PlaylistResponse,
)
from app.services.dataset import get_dataset_features
from app.services.ordering import get_transition_scores_for_ids, order_track_ids
from app.services.spotify_playlists import create_playlist
from app.utils.dependencies import get_spotify_client

router = APIRouter(
    tags=["Playlists"],
)


@router.post("/playlists/order", response_model=PlaylistOrderResponse)
def order_playlist(request: PlaylistOrderRequest):
    """Arrange songs so tempo, energy, and mood change gradually from one to the
    next ("smooth flow"). No login needed; nothing is saved."""
    track_ids = list(dict.fromkeys(request.track_ids))  # remove duplicates, keep order

    features = get_dataset_features(track_ids)
    ordered = order_track_ids(track_ids, features)

    return PlaylistOrderResponse(
        track_ids=ordered,
        transition_scores=get_transition_scores_for_ids(ordered, features),
        unordered_ids=[track_id for track_id in ordered if track_id not in features],
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
