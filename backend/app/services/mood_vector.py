import numpy as np

from app.services.feature_scaling import scale_vectors
from app.services.mood_analysis import extract_mood_terms
from app.services.mood_targets import create_target_vector


def create_mood_vector(description: str) -> np.ndarray:
    """Convert a mood description into a target vector.

    The vector has the same attributes, in the same order, as
    create_song_vector(): energy, tempo, valence, acousticness,
    danceability, instrumentalness. Tempo is in beats per minute.

    A description with no recognizable mood terms gives the neutral vector.
    """
    mood_terms = extract_mood_terms(description)

    return create_target_vector(mood_terms)


def create_scaled_mood_vector(description: str) -> np.ndarray:
    """Mood vector on the same 0–1 scale as create_scaled_song_vector(),
    so the two can be compared directly."""
    return scale_vectors(create_mood_vector(description))[0]
