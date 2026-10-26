import requests

from app.models.audio_features import AudioFeatures

RECCOBEATS_URL = "https://api.reccobeats.com/v1/audio-features"
MAX_IDS_PER_REQUEST = 40   # ReccoBeats rejects more than 40 IDs per request


def get_audio_features(track_ids: list[str]):
    track_ids = list(dict.fromkeys(track_ids))   # remove duplicates, keep order
    features = {}

    for start in range(0, len(track_ids), MAX_IDS_PER_REQUEST):
        batch = track_ids[start:start + MAX_IDS_PER_REQUEST]

        try:
            response = requests.get(
                RECCOBEATS_URL,
                params={"ids": ",".join(batch)},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue   # ReccoBeats is down or rate-limited; these tracks stay missing

        for item in response.json().get("content", []):
            track_id = item["href"].rsplit("/", 1)[-1]
            features[track_id] = AudioFeatures(track_id=track_id, **item)

    return features
