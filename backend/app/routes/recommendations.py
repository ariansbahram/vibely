import spotipy

from fastapi import APIRouter, Depends, HTTPException

from app.models.recommendation import RecommendationRequest, RecommendationResponse
from app.services.mood_analysis import extract_mood_terms
from app.services.mood_targets import get_target_features
from app.services.playlist_title import generate_playlist_title
from app.services.recommender import DatasetUnavailableError, recommend_tracks
from app.utils.dependencies import get_optional_spotify_client

router = APIRouter(
    tags=["Recommendations"],
)


@router.post("/recommendations", response_model=RecommendationResponse)
def create_recommendations(
    request: RecommendationRequest,
    spotify: spotipy.Spotify | None = Depends(get_optional_spotify_client),
):
    # FastAPI has already validated the body against RecommendationRequest;
    # invalid input never reaches this point (it gets a 422 response).

    filters = request.filters

    # Only Spotify knows which songs are explicit, so this filter needs a login.
    # Without one, every song would be left out (unknown counts as possibly explicit).
    if filters is not None and not filters.allow_explicit and spotify is None:
        raise HTTPException(
            status_code=401,
            detail="Log in to Spotify to filter out explicit songs.",
        )

    mood_terms = extract_mood_terms(request.mood)

    try:
        recommendations = recommend_tracks(
            request.mood,
            filters,
            limit=request.limit,
            max_per_artist=request.max_per_artist,
            spotify=spotify,
        )
    except DatasetUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="The song dataset isn't downloaded. See 'Download the dataset' in the README.",
        )

    return RecommendationResponse(
        mood=request.mood,
        mood_terms=mood_terms,
        target_features=get_target_features(mood_terms),
        playlist_title=generate_playlist_title(request.mood, mood_terms),
        recommendations=recommendations,
    )
