import spotipy

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.track import Track
from app.services.spotify_search import search_tracks
from app.utils.dependencies import get_spotify_client

router = APIRouter(
    tags=["Spotify Search"],
)


@router.get("/search", response_model=list[Track])
def search(
    q: str = Query(..., description="Song, artist, or keyword"),
    limit: int = Query(10, ge=1, le=10),
    spotify: spotipy.Spotify = Depends(get_spotify_client),
):
    query = q.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    return search_tracks(spotify, query, limit)
