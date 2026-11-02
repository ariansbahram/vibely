from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.models.audio_features import AudioFeatures


DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "spotify_data.csv"

FEATURE_COLUMNS = [
    "acousticness",
    "danceability",
    "energy",
    "instrumentalness",
    "liveness",
    "loudness",
    "speechiness",
    "tempo",
    "valence",
    "key",
    "mode",
]


@lru_cache(maxsize=1)
def load_dataset():
    if not DATASET_PATH.exists():
        return None

    dataset = pd.read_csv(DATASET_PATH)

    # Normalize column names
    dataset.columns = (
        dataset.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Remove unnecessary saved index column
    dataset = dataset.drop(
        columns=["unnamed:_0"],
        errors="ignore"
    )

    # Keep only the columns Vibely needs
    required_columns = ["track_id", *FEATURE_COLUMNS]
    dataset = dataset[required_columns].copy()

    # Remove rows without a Spotify track ID
    dataset = dataset.dropna(subset=["track_id"])

    # Remove duplicate tracks
    dataset = dataset.drop_duplicates(
        subset=["track_id"],
        keep="first"
    )

    # Convert feature columns to numeric values
    for column in FEATURE_COLUMNS:
        dataset[column] = pd.to_numeric(
            dataset[column],
            errors="coerce"
        )

    # Remove tracks missing important recommendation features
    dataset = dataset.dropna(
        subset=[
            "energy",
            "tempo",
            "valence",
            "acousticness",
            "danceability",
            "instrumentalness",
        ]
    )

    # Remove invalid feature values
    dataset = dataset[
        dataset["energy"].between(0, 1)
        & dataset["valence"].between(0, 1)
        & dataset["acousticness"].between(0, 1)
        & dataset["danceability"].between(0, 1)
        & dataset["instrumentalness"].between(0, 1)
        & (dataset["tempo"] > 0)
    ]

    return dataset.set_index("track_id")


def get_dataset_features(track_ids: list[str]):
    dataset = load_dataset()

    if dataset is None:
        return {}

    found = dataset.loc[
        dataset.index.intersection(track_ids)
    ]

    return {
        track_id: AudioFeatures(
            track_id=track_id,
            **{
                column: row[column]
                for column in FEATURE_COLUMNS
            }
        )
        for track_id, row in found.iterrows()
    }