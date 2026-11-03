from functools import lru_cache

import numpy as np
from sklearn.preprocessing import MinMaxScaler

from app.models.audio_features import AudioFeatures
from app.services.dataset import load_dataset
from app.services.feature_vector import RECOMMENDATION_FEATURES, create_song_vector

# Used when the dataset isn't downloaded: typical (min, max) for each feature
DEFAULT_RANGES = {
    "energy": (0.0, 1.0),
    "tempo": (0.0, 250.0),
    "valence": (0.0, 1.0),
    "acousticness": (0.0, 1.0),
    "danceability": (0.0, 1.0),
    "instrumentalness": (0.0, 1.0),
}


@lru_cache(maxsize=1)
def get_scaler():
    scaler = MinMaxScaler(clip=True)
    dataset = load_dataset()

    if dataset is None:
        lows = [DEFAULT_RANGES[feature][0] for feature in RECOMMENDATION_FEATURES]
        highs = [DEFAULT_RANGES[feature][1] for feature in RECOMMENDATION_FEATURES]
        return scaler.fit(np.array([lows, highs]))

    return scaler.fit(dataset[RECOMMENDATION_FEATURES].to_numpy())


def scale_vectors(vectors: np.ndarray) -> np.ndarray:
    return get_scaler().transform(np.atleast_2d(vectors))


def create_scaled_song_vector(features: AudioFeatures) -> np.ndarray:
    return scale_vectors(create_song_vector(features))[0]
