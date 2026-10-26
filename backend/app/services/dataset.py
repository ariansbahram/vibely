from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.models.audio_features import AudioFeatures

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "spotify_data.csv"

FEATURE_COLUMNS = [
    "acousticness", "danceability", "energy", "instrumentalness", "liveness",
    "loudness", "speechiness", "tempo", "valence", "key", "mode",
]


@lru_cache(maxsize=1)
def load_dataset():
    if not DATASET_PATH.exists():
        return None   # dataset not downloaded; the backup is simply skipped

    dataset = pd.read_csv(DATASET_PATH, usecols=["track_id", *FEATURE_COLUMNS])
    return dataset.set_index("track_id")


def get_dataset_features(track_ids: list[str]):
    dataset = load_dataset()
    if dataset is None:
        return {}

    found = dataset.loc[dataset.index.intersection(track_ids)]

    return {
        track_id: AudioFeatures(track_id=track_id, **row)
        for track_id, row in found.to_dict("index").items()
    }
