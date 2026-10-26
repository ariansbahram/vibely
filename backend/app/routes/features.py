from fastapi import APIRouter, HTTPException, Query

from app.services.feature_lookup import get_features_with_backup

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
    features, from_dataset = get_features_with_backup(track_ids)

    return {
        "features": list(features.values()),
        "from_dataset": from_dataset,
        "missing": [track_id for track_id in track_ids if track_id not in features],
    }
