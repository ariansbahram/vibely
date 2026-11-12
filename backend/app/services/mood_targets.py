import numpy as np

from app.services.feature_vector import RECOMMENDATION_FEATURES

# What an "average" song looks like, close to the middle of the Kaggle dataset.
# Used for any feature the mood terms say nothing about.
NEUTRAL_TARGETS = {
    "energy": 0.65,
    "tempo": 120.0,
    "valence": 0.45,
    "acousticness": 0.30,
    "danceability": 0.55,
    "instrumentalness": 0.10,
}

# The musical characteristics each mood term points to.
# All values are 0–1 except tempo, which is in beats per minute.
# A term only lists the features it has an opinion about; "rainy" says
# nothing about danceability, so it leaves danceability alone.
MOOD_TARGETS = {
    # Feelings
    "happy": {"valence": 0.85, "energy": 0.70, "danceability": 0.70, "tempo": 120.0},
    "sad": {"valence": 0.15, "energy": 0.30, "acousticness": 0.60, "tempo": 85.0, "danceability": 0.35},
    "melancholic": {"valence": 0.25, "energy": 0.35, "acousticness": 0.55, "tempo": 90.0},
    "heartbroken": {"valence": 0.15, "energy": 0.35, "acousticness": 0.55, "tempo": 85.0},
    "lonely": {"valence": 0.20, "energy": 0.30, "acousticness": 0.60, "tempo": 85.0},
    "angry": {"valence": 0.25, "energy": 0.92, "acousticness": 0.05, "tempo": 145.0},
    "anxious": {"valence": 0.45, "energy": 0.30, "acousticness": 0.65, "tempo": 80.0, "instrumentalness": 0.40},
    "romantic": {"valence": 0.60, "energy": 0.45, "acousticness": 0.50, "tempo": 95.0, "danceability": 0.55},
    "nostalgic": {"valence": 0.40, "energy": 0.45, "acousticness": 0.50, "tempo": 100.0},
    "hopeful": {"valence": 0.70, "energy": 0.60, "tempo": 115.0},
    "confident": {"valence": 0.70, "energy": 0.80, "danceability": 0.75, "tempo": 115.0},
    "dreamy": {"valence": 0.45, "energy": 0.35, "acousticness": 0.50, "tempo": 95.0, "instrumentalness": 0.40},
    "dark": {"valence": 0.15, "energy": 0.55, "acousticness": 0.20, "tempo": 110.0},
    # Energy level
    "energetic": {"energy": 0.90, "tempo": 140.0, "danceability": 0.70, "acousticness": 0.10},
    "upbeat": {"valence": 0.80, "energy": 0.80, "tempo": 125.0, "danceability": 0.75},
    "calm": {"energy": 0.25, "tempo": 80.0, "acousticness": 0.75, "valence": 0.50},
    "chill": {"energy": 0.40, "tempo": 90.0, "acousticness": 0.50, "valence": 0.55, "danceability": 0.60},
    "sleepy": {"energy": 0.12, "tempo": 70.0, "acousticness": 0.85, "instrumentalness": 0.60, "danceability": 0.30},
    # Time and weather
    "late night": {"energy": 0.40, "tempo": 95.0, "valence": 0.35, "acousticness": 0.35},
    "morning": {"energy": 0.50, "tempo": 105.0, "valence": 0.65, "acousticness": 0.50},
    "rainy": {"energy": 0.30, "tempo": 85.0, "valence": 0.30, "acousticness": 0.70},
    "sunny": {"energy": 0.70, "tempo": 115.0, "valence": 0.80, "danceability": 0.70},
    "cozy": {"energy": 0.30, "tempo": 85.0, "valence": 0.55, "acousticness": 0.75},
    # Activities
    "focused": {"energy": 0.35, "tempo": 95.0, "acousticness": 0.55, "instrumentalness": 0.80},
    "workout": {"energy": 0.92, "tempo": 140.0, "danceability": 0.70, "acousticness": 0.05, "valence": 0.60},
    "party": {"energy": 0.85, "tempo": 125.0, "danceability": 0.85, "valence": 0.75, "acousticness": 0.05},
    "road trip": {"energy": 0.70, "tempo": 120.0, "valence": 0.65, "danceability": 0.60},
}


def get_target_features(mood_terms: list[str]) -> dict[str, float]:
    """Combine mood terms into one target value per audio feature.

    Each feature is the average of the values from the terms that mention it,
    so ["energetic", "sad"] meets in the middle on energy. Features that no
    term mentions, and terms that aren't in MOOD_TARGETS, fall back to neutral.
    """
    targets = {}

    for feature in RECOMMENDATION_FEATURES:
        values = [
            MOOD_TARGETS[term][feature]
            for term in mood_terms
            if feature in MOOD_TARGETS.get(term, {})
        ]

        if values:
            targets[feature] = round(sum(values) / len(values), 3)
        else:
            targets[feature] = NEUTRAL_TARGETS[feature]

    return targets


def create_target_vector(mood_terms: list[str]) -> np.ndarray:
    """Target features as a vector in the same order as create_song_vector()."""
    targets = get_target_features(mood_terms)

    return np.array(
        [targets[feature] for feature in RECOMMENDATION_FEATURES],
        dtype=float,
    )
