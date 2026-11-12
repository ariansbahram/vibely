import numpy as np
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances

from app.models.audio_features import AudioFeatures
from app.services.feature_scaling import scale_vectors
from app.services.feature_vector import RECOMMENDATION_FEATURES, create_song_vector
from app.services.mood_vector import create_scaled_mood_vector

# The largest possible distance between two scaled vectors:
# every feature is 0–1, so it's the diagonal of a cube with one side per feature.
MAX_DISTANCE = np.sqrt(len(RECOMMENDATION_FEATURES))


def calculate_similarity_scores(
    mood_vector: np.ndarray,
    song_vectors: np.ndarray,
    metric: str = "cosine",
) -> np.ndarray:
    """Score every song vector against the mood vector. Higher means more similar.

    Both inputs must already be scaled to 0–1 (see scale_vectors()).
    song_vectors has one row per song; the result has one score per row.

    metric:
      "cosine"    – cosine similarity: compares the direction of the vectors,
                    i.e. the balance between features. 1.0 is a perfect match.
      "euclidean" – straight-line distance turned into a 0–1 score:
                    1.0 is identical, 0.0 is as far apart as possible.
    """
    mood_vector = np.atleast_2d(mood_vector)
    song_vectors = np.atleast_2d(song_vectors)

    if metric == "cosine":
        return cosine_similarity(mood_vector, song_vectors)[0]

    if metric == "euclidean":
        distances = euclidean_distances(mood_vector, song_vectors)[0]
        return 1 - distances / MAX_DISTANCE

    raise ValueError(f"Unknown metric: {metric!r}. Use 'cosine' or 'euclidean'.")


def score_tracks(
    description: str,
    candidates: list[AudioFeatures],
    metric: str = "cosine",
) -> dict[str, float]:
    """Compare a mood description against candidate tracks.

    Returns {track_id: similarity score}, best match first.
    """
    if not candidates:
        return {}

    mood_vector = create_scaled_mood_vector(description)
    song_vectors = scale_vectors(
        np.array([create_song_vector(features) for features in candidates])
    )

    scores = calculate_similarity_scores(mood_vector, song_vectors, metric)

    scored_tracks = sorted(
        zip(candidates, scores),
        key=lambda pair: pair[1],
        reverse=True,
    )

    return {
        features.track_id: round(float(score), 4)
        for features, score in scored_tracks
    }
