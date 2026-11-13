import spotipy

from fastapi import APIRouter, Depends, HTTPException

from app.models.recommendation import (
    MoreRecommendationsRequest,
    MoreRecommendationsResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.mood_interpretation import interpret_mood
from app.services.recommender import DatasetUnavailableError, get_dataset_tracks, recommend_tracks
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

    # What the songs should sound like, from the word lists and, if the
    # frontend's AI read the description, its vibe too
    mood = interpret_mood(request.mood, request.vibe)

    try:
        recommendations = recommend_tracks(
            mood.target_features,
            mood.preferred_genres,
            filters,
            genre_affinity=mood.genre_affinity,
            limit=request.limit,
            max_per_artist=request.max_per_artist,
            spotify=spotify,
            featured_artists=mood.featured_artists,
            artist_share=mood.artist_share,
            year_range=mood.year_range,
            languages=mood.languages,
            fit_profile=mood.fit_profile,
            exclude_ids=set(mood.exclude_ids),
        )
    except DatasetUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="The song dataset isn't downloaded. See 'Download the dataset' in the README.",
        )

    return RecommendationResponse(
        mood=request.mood,
        mood_terms=mood.mood_terms,
        understood_by=mood.understood_by,
        target_features=mood.target_features,
        preferred_genres=mood.preferred_genres,
        genre_affinity=mood.genre_affinity,
        notes=mood.notes,
        playlist_title=mood.playlist_title,
        recommendations=recommendations,
    )


@router.post("/recommendations/more", response_model=MoreRecommendationsResponse)
def more_recommendations(
    request: MoreRecommendationsRequest,
    spotify: spotipy.Spotify | None = Depends(get_optional_spotify_client),
):
    """New songs for the same description that aren't in the playlist yet, e.g.
    to replace songs the user removed. Send the same mood and vibe as the
    /recommendations request."""
    filters = request.filters
    mood = interpret_mood(request.mood, request.vibe)

    if filters is not None and not filters.allow_explicit and spotify is None:
        raise HTTPException(
            status_code=401,
            detail="Log in to Spotify to filter out explicit songs.",
        )

    try:
        recommendations = recommend_tracks(
            mood.target_features,
            mood.preferred_genres,
            filters,
            limit=request.limit,
            max_per_artist=request.max_per_artist,
            spotify=spotify,
            exclude_ids=set(request.exclude_ids) | set(mood.exclude_ids),
            taken=get_dataset_tracks(request.playlist_ids),
            genre_affinity=mood.genre_affinity,
            featured_artists=mood.featured_artists,
            artist_share=mood.artist_share,
            year_range=mood.year_range,
            languages=mood.languages,
            fit_profile=mood.fit_profile,
        )
    except DatasetUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="The song dataset isn't downloaded. See 'Download the dataset' in the README.",
        )

    return MoreRecommendationsResponse(recommendations=recommendations)
