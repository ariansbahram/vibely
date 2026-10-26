from fastapi import APIRouter, HTTPException, Query

from app.services.roccobeats import get_audio_features

router = APIRouter(
    tags=["Audio Features"],
)


@router.get("/audio-features")
def read_audio_features(
    ids: str = Query(..., description="Comma-separated Spotify track IDs"),
):
    track_ids = [track_id.strip() for track_id in ids.split(",") if track_id.strip()]

    if not track_ids:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one Spotify track ID.",
        )

    if len(track_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="At most 100 track IDs per request.",
        )

    features = get_audio_features(track_ids)

    return {
        "features": list(features.values()),
        "missing": [track_id for track_id in track_ids if track_id not in features],
    }
