import numpy as np

from app.models.audio_features import AudioFeatures


RECOMMENDATION_FEATURES = [
    "energy",
    "tempo",
    "valence",
    "acousticness",
    "danceability",
    "instrumentalness",
]


def create_song_vector(features: AudioFeatures) -> np.ndarray:
    return np.array(
        [
            features.energy,
            features.tempo,
            features.valence,
            features.acousticness,
            features.danceability,
            features.instrumentalness,
        ],
        dtype=float,
    )