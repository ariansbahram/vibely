from functools import lru_cache

import numpy as np
import spotipy

from app.models.recommendation import RecommendationFilters, RecommendedTrack
from app.models.track import Track
from app.services.dataset import get_dataset_features, load_dataset
from app.services.feature_scaling import scale_vectors
from app.services.feature_vector import RECOMMENDATION_FEATURES
from app.services.filters import filter_tracks, normalize_name
from app.services.mood_vector import create_scaled_mood_vector
from app.services.ranking import rank_tracks
from app.services.similarity import calculate_similarity_scores
from app.services.track_details import add_track_details

# Euclidean scores spread out more than cosine ones (where most songs score ~0.9),
# so the number shown to the user means more. See "Similarity scores" in the README.
SIMILARITY_METRIC = "euclidean"

# How many top-scoring songs to look at per song returned. rank_tracks() drops
# duplicate songs and caps each artist, so it needs more candidates than it returns.
CANDIDATES_PER_RESULT = 20

# With the explicit filter, Spotify details are fetched for this many times the
# requested number of songs, so there is room left after explicit songs are removed.
EXPLICIT_FILTER_HEADROOM = 3


class DatasetUnavailableError(Exception):
    """The Kaggle dataset isn't downloaded, so there are no songs to recommend."""


@lru_cache(maxsize=1)
def get_scaled_dataset_vectors() -> np.ndarray:
    """Every dataset song as a scaled vector, one row per song (computed once)."""
    return scale_vectors(load_dataset()[RECOMMENDATION_FEATURES].to_numpy())


@lru_cache(maxsize=1)
def get_normalized_names() -> tuple[np.ndarray, np.ndarray]:
    """Every song's genre and artist, normalized the way the filters compare them."""
    dataset = load_dataset()

    return (
        dataset["genre"].fillna("").map(normalize_name).to_numpy(),
        dataset["artist_name"].map(normalize_name).to_numpy(),
    )


def get_filter_mask(filters: RecommendationFilters | None) -> np.ndarray:
    """True for every dataset song that passes the filters the dataset can check.

    Same rules as filter_tracks(), applied to the whole dataset at once.
    The explicit filter is checked later: the dataset doesn't say which songs are explicit.
    """
    dataset = load_dataset()
    mask = np.ones(len(dataset), dtype=bool)

    if filters is None:
        return mask

    genres, artists = get_normalized_names()

    if filters.genres:
        mask &= np.isin(genres, [normalize_name(genre) for genre in filters.genres])

    if filters.artists:
        mask &= np.isin(artists, [normalize_name(artist) for artist in filters.artists])

    popularity = dataset["popularity"].to_numpy()
    years = dataset["year"].to_numpy()

    if filters.min_popularity is not None:
        mask &= popularity >= filters.min_popularity

    if filters.max_popularity is not None:
        mask &= popularity <= filters.max_popularity

    if filters.min_year is not None:
        mask &= years >= filters.min_year

    if filters.max_year is not None:
        mask &= years <= filters.max_year

    return mask


def get_candidates(
    mood: str,
    filters: RecommendationFilters | None,
    count: int,
) -> tuple[list[Track], dict[str, float]]:
    """The `count` dataset songs closest to the mood that pass the filters,
    with their scores ({track_id: score})."""
    dataset = load_dataset()

    allowed = np.flatnonzero(get_filter_mask(filters))

    if allowed.size == 0:
        return [], {}

    scores = calculate_similarity_scores(
        create_scaled_mood_vector(mood),
        get_scaled_dataset_vectors()[allowed],
        SIMILARITY_METRIC,
    )

    # The top `count` scores, without sorting the rest (rank_tracks() sorts these)
    count = min(count, allowed.size)
    best = np.argpartition(scores, -count)[-count:]

    rows = dataset.iloc[allowed[best]]

    tracks = [
        Track(
            id=track_id,
            title=row.track_name,
            artists=[row.artist_name],
            spotify_url=f"https://open.spotify.com/track/{track_id}",
            genre=row.genre,
            popularity=int(row.popularity),
            release_year=int(row.year),
        )
        for track_id, row in zip(rows.index, rows.itertuples(index=False))
    ]

    track_scores = {
        track.id: round(float(score), 4)
        for track, score in zip(tracks, scores[best])
    }

    return tracks, track_scores


def recommend_tracks(
    mood: str,
    filters: RecommendationFilters | None = None,
    limit: int = 10,
    max_per_artist: int | None = None,
    spotify: spotipy.Spotify | None = None,
) -> list[RecommendedTrack]:
    """Songs from the dataset that match a mood description, best match first.

    Each song comes with its similarity score, audio features, and, where they
    can be found, its album and album artwork. Those come from Spotify when the
    user is logged in (`spotify`), otherwise only the artwork is looked up.

    Raises DatasetUnavailableError if the dataset isn't downloaded.
    """
    if load_dataset() is None:
        raise DatasetUnavailableError

    tracks, scores = get_candidates(mood, filters, limit * CANDIDATES_PER_RESULT)

    filtering_explicit = filters is not None and not filters.allow_explicit
    detail_count = limit * EXPLICIT_FILTER_HEADROOM if filtering_explicit else limit

    ranked = rank_tracks(tracks, scores, limit=detail_count, max_per_artist=max_per_artist)
    ranked = add_track_details(ranked, spotify)

    # The details from Spotify include the explicit flag, so the filters are
    # checked again now. The other filters already passed and still do.
    ranked = filter_tracks(ranked, filters)[:limit]

    features = get_dataset_features([track.id for track in ranked])

    return [
        track.model_copy(update={"audio_features": features[track.id]})
        for track in ranked
    ]
