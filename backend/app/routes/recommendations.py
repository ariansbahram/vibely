from fastapi import APIRouter

from app.models.recommendation import RecommendationRequest, RecommendationResponse
from app.services.mood_analysis import extract_mood_terms
from app.services.mood_targets import get_target_features

router = APIRouter(
    tags=["Recommendations"],
)


@router.post("/recommendations", response_model=RecommendationResponse)
def create_recommendations(request: RecommendationRequest):
    # FastAPI has already validated the body against RecommendationRequest;
    # invalid input never reaches this point (it gets a 422 response).

    mood_terms = extract_mood_terms(request.mood)

    target_features = get_target_features(mood_terms)

    # TODO: get candidate tracks, then:
    #   filter_tracks(candidates, request.filters)  -> only tracks the user allows
    #   score_tracks(request.mood, features)        -> similarity score per track
    #   rank_tracks(candidates, scores)             -> top matches
    return RecommendationResponse(
        mood=request.mood,
        mood_terms=mood_terms,
        target_features=target_features,
        recommendations=[],
    )
