import numpy as np

from app.models.audio_features import AudioFeatures
from app.models.track import Track
from app.services.feature_scaling import scale_vectors
from app.services.feature_vector import RECOMMENDATION_FEATURES, create_song_vector

# The features a listener notices when one song ends and the next begins,
# and how much each one counts. Valence is the mood (sad to happy).
# Tempo counts double because scaling squeezes it: the scale covers 30–250 BPM,
# but most songs sit between 80 and 165, so real tempo jumps look small.
# Acousticness and danceability count half: going from an acoustic song to an
# electronic one is noticeable, but less jarring than a change of pace or mood.
TRANSITION_WEIGHTS = {
    "energy": 1.0,
    "tempo": 2.0,
    "valence": 1.0,
    "acousticness": 0.5,
    "danceability": 0.5,
}

# The most improvements to make before settling for the current order
MAX_IMPROVEMENT_PASSES = 200


def create_transition_vectors(
    features: list[AudioFeatures],
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """One row per song with only the weighted transition features, scaled to 0–1 first."""
    weights = TRANSITION_WEIGHTS if weights is None else weights

    unknown = [name for name in weights if name not in RECOMMENDATION_FEATURES]
    if unknown:
        raise ValueError(
            f"Unknown attributes: {unknown}. Choose from {RECOMMENDATION_FEATURES}."
        )

    scaled = scale_vectors(
        np.array([create_song_vector(song) for song in features])
    )

    columns = [RECOMMENDATION_FEATURES.index(name) for name in weights]

    return scaled[:, columns] * np.array(list(weights.values()))


def transition_score(
    track_a: AudioFeatures,
    track_b: AudioFeatures,
    weights: dict[str, float] | None = None,
) -> float:
    """How smoothly one song leads into another, from 0 to 1.

    1.0 means the two songs are identical on every compared attribute;
    0.0 means they are as different as possible on all of them.
    The order doesn't matter: a -> b scores the same as b -> a.

    weights  – which attributes to compare and how much each counts,
               e.g. {"tempo": 1.0, "energy": 1.0}. Defaults to TRANSITION_WEIGHTS
               (tempo, energy, valence, acousticness, danceability).
    """
    weights = TRANSITION_WEIGHTS if weights is None else weights

    vector_a, vector_b = create_transition_vectors([track_a, track_b], weights)
    distance = np.linalg.norm(vector_a - vector_b)

    # The largest possible distance: every attribute differs by the full 0–1 range
    max_distance = np.linalg.norm(list(weights.values()))

    if max_distance == 0:
        return 1.0

    return round(float(1 - distance / max_distance), 4)


def get_transition_sizes(vectors: np.ndarray, order: list[int]) -> np.ndarray:
    """The size of each jump between neighboring songs when played in this order."""
    ordered = vectors[order]

    return np.linalg.norm(ordered[1:] - ordered[:-1], axis=1)


def find_smooth_order(vectors: np.ndarray) -> list[int]:
    """Arrange the rows so neighbors are as alike as possible. Row 0 stays first."""
    count = len(vectors)

    # Step 1: start at the first song, then keep moving to the closest song not used yet
    order = [0]
    remaining = set(range(1, count))

    while remaining:
        current = vectors[order[-1]]
        closest = min(remaining, key=lambda index: np.linalg.norm(vectors[index] - current))
        order.append(closest)
        remaining.remove(closest)

    # Step 2: the step above can leave a big jump near the end, when only
    # far-away songs are left. Try small changes to the order and keep each
    # one that makes the whole playlist smoother, until nothing helps anymore.
    best_total = get_transition_sizes(vectors, order).sum()

    for _ in range(MAX_IMPROVEMENT_PASSES):
        improved = False

        for candidate in get_order_changes(order):
            total = get_transition_sizes(vectors, candidate).sum()

            if total < best_total - 1e-9:
                order, best_total = candidate, total
                improved = True
                break  # the changes were built from the old order; start over

        if not improved:
            break

    return order


def get_order_changes(order: list[int]):
    """Every order reachable by one small change. The first song never moves."""
    count = len(order)

    # Reverse a stretch: [A, B, C, D, E] -> [A, D, C, B, E]
    for start in range(1, count - 1):
        for end in range(start + 1, count):
            yield order[:start] + order[start:end + 1][::-1] + order[end + 1:]

    # Move one song somewhere else: [A, B, C, D, E] -> [A, C, D, B, E]
    for position in range(1, count):
        without_song = order[:position] + order[position + 1:]

        for new_position in range(1, count):
            if new_position != position:
                yield without_song[:new_position] + [order[position]] + without_song[new_position:]


def order_tracks(
    tracks: list[Track],
    features: dict[str, AudioFeatures],
) -> list[Track]:
    """Reorder recommended tracks so the playlist flows from one song to the next.

    The order chosen is the one with the highest total transition_score()
    between neighbors that the search can find.

    tracks    – the recommended tracks, best match first (e.g. from rank_tracks())
    features  – {track_id: AudioFeatures} for those tracks

    The first track stays first, so the playlist opens with the best match.
    After that, songs are arranged so that tempo, energy, mood, and the other
    attributes in TRANSITION_WEIGHTS change as little as possible between
    neighbors (the same comparison transition_score() makes). The same tracks are returned;
    only the order changes.

    Tracks without audio features can't be compared, so they go at the end
    in their original order.
    """
    with_features = [track for track in tracks if track.id in features]
    without_features = [track for track in tracks if track.id not in features]

    if len(with_features) < 3:
        # With one or two songs there is nothing to rearrange
        return with_features + without_features

    vectors = create_transition_vectors(
        [features[track.id] for track in with_features]
    )

    order = find_smooth_order(vectors)

    return [with_features[index] for index in order] + without_features


def order_track_ids(
    track_ids: list[str],
    features: dict[str, AudioFeatures],
) -> list[str]:
    """order_tracks() for plain track IDs: the same IDs in smooth-flow order.

    The first ID stays first. IDs without audio features go at the end.
    """
    with_features = [track_id for track_id in track_ids if track_id in features]
    without_features = [track_id for track_id in track_ids if track_id not in features]

    if len(with_features) < 3:
        return with_features + without_features

    vectors = create_transition_vectors([features[track_id] for track_id in with_features])
    order = find_smooth_order(vectors)

    return [with_features[index] for index in order] + without_features


def get_transition_scores_for_ids(
    track_ids: list[str],
    features: dict[str, AudioFeatures],
) -> list[float | None]:
    """get_playlist_transition_scores() for plain track IDs."""
    return [
        transition_score(features[current], features[following])
        if current in features and following in features
        else None
        for current, following in zip(track_ids, track_ids[1:])
    ]


def get_playlist_transition_scores(
    tracks: list[Track],
    features: dict[str, AudioFeatures],
) -> list[float | None]:
    """The transition score between each pair of neighboring tracks, in playlist order.

    A playlist of 10 tracks has 9 transitions. A transition is None when
    either track has no audio features.
    """
    return [
        transition_score(features[current.id], features[following.id])
        if current.id in features and following.id in features
        else None
        for current, following in zip(tracks, tracks[1:])
    ]
