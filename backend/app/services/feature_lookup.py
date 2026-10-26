from app.services.dataset import get_dataset_features
from app.services.roccobeats import get_audio_features


def get_features_with_backup(track_ids: list[str]):
    features = get_audio_features(track_ids)

    missing = [track_id for track_id in track_ids if track_id not in features]
    from_dataset = get_dataset_features(missing) if missing else {}

    features.update(from_dataset)
    return features, list(from_dataset)
