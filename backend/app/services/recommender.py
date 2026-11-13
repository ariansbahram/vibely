import math
from functools import lru_cache

import numpy as np
import pandas as pd
import spotipy

from app.models.recommendation import RecommendationFilters, RecommendedTrack
from app.models.track import Track
from app.services.dataset import get_dataset_features, load_dataset
from app.services.feature_scaling import scale_vectors
from app.services.feature_vector import RECOMMENDATION_FEATURES
from app.services.filters import filter_tracks, normalize_name
from app.services.language import get_language_mask, get_song_languages
from app.services.ranking import rank_tracks
from app.services.track_details import add_track_details

# How a song's match score is made up (see get_fit_scores()):
#   audio      – how close its tempo, energy, mood, etc. are to the target
#   genre      – how well its genre suits the mood (GENRE_AFFINITY)
#   popularity – a little preference for songs people might know
# Without a genre opinion (no known mood words), audio and popularity share it all.
FIT_WEIGHTS = {"audio": 0.6, "genre": 0.3, "popularity": 0.1}
FIT_WEIGHTS_WITHOUT_GENRES = {"audio": 0.85, "genre": 0.0, "popularity": 0.15}

# For "taylor swift" on its own: her best-known songs first. Popularity here
# isn't capped at FULL_POPULARITY ("raw"), so Anti-Hero (92) beats a deep cut (60).
ARTIST_ONLY_WEIGHTS = {"audio": 0.3, "genre": 0.0, "popularity": 0.0, "raw_popularity": 0.7}

# For a decade or year ("early 2010s throwbacks"): the hits of the time count
# more, by uncapped popularity, so a 2012 chart hit beats a well-liked album track
ERA_WEIGHTS = {"audio": 0.4, "genre": 0.2, "popularity": 0.0, "raw_popularity": 0.4}

# For songs like a named song or artist ("songs like cruel summer"): sound first,
# and well-known songs count more, since the song asked about is one
REFERENCE_WEIGHTS = {"audio": 0.5, "genre": 0.25, "popularity": 0.0, "raw_popularity": 0.25}
FIT_PROFILES = {"era": ERA_WEIGHTS, "reference": REFERENCE_WEIGHTS}

# Songs by an artist the user named fully match that part of the description,
# so this much of their shown score is a given; the rest is how well they fit the mood
ARTIST_MATCH_CREDIT = 0.4


# Popularity at or above this counts as fully popular (Spotify's 0–100 scale;
# half the dataset is at 15 or below)
FULL_POPULARITY = 60

# Songs left out unless the user asks for specific genres: live recordings,
# spoken word, and stand-up comedy match moods by their numbers but rarely fit
MAX_LIVENESS = 0.8
MAX_SPEECHINESS = 0.66
EXCLUDED_GENRES = {"comedy"}

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
def get_quality_mask() -> np.ndarray:
    """False for live recordings, spoken word, and comedy (computed once)."""
    dataset = load_dataset()

    return (
        (dataset["liveness"].fillna(0).to_numpy() <= MAX_LIVENESS)
        & (dataset["speechiness"].fillna(0).to_numpy() <= MAX_SPEECHINESS)
        & ~dataset["genre"].isin(EXCLUDED_GENRES).to_numpy()
    )


@lru_cache(maxsize=1)
def get_genre_codes() -> tuple[np.ndarray, list[str]]:
    """Every song's genre as a number, and the genre names those numbers stand for."""
    genres = load_dataset()["genre"].fillna("").astype("category")
    return genres.cat.codes.to_numpy(), list(genres.cat.categories)


@lru_cache(maxsize=1)
def get_raw_popularity() -> np.ndarray:
    """Every song's popularity as 0–1, not capped."""
    return load_dataset()["popularity"].fillna(0).to_numpy(dtype=float) / 100


def warm_up() -> None:
    """Load the dataset and build every cache, so the first request isn't slow."""
    if load_dataset() is None:
        return

    get_scaled_dataset_vectors()
    get_quality_mask()
    get_genre_codes()
    get_popularity_fit()
    get_raw_popularity()
    get_song_languages()
    get_normalized_names()


@lru_cache(maxsize=1)
def get_popularity_fit() -> np.ndarray:
    """Every song's popularity as 0–1, capped at FULL_POPULARITY."""
    popularity = load_dataset()["popularity"].fillna(0).to_numpy(dtype=float)
    return np.clip(popularity / FULL_POPULARITY, 0, 1)


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

    # Unless the user picked genres, leave out live recordings, spoken word, and comedy
    if not (filters and filters.genres):
        mask &= get_quality_mask()

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


def get_fit_scores(
    target_features: dict[str, float],
    genre_affinity: dict[str, float],
    rows: np.ndarray,
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """How well each song (dataset row numbers in `rows`) fits the mood, 0–1.

    audio fit:  1.0 for a song exactly on the target, 0.0 for one as far from it
                as a typical song (the median distance). Raw distance can't be
                shown as-is: with 1.16M songs, dozens sit almost exactly on any
                target and half of all songs would look like a 70%+ match.
    genre fit:  genre_affinity for the song's genre (0 if not listed)
    popularity: see get_popularity_fit()

    Combined with FIT_WEIGHTS, so a song needs the right sound AND a fitting
    genre to score high.
    """
    target_vector = scale_vectors(
        np.array([target_features[feature] for feature in RECOMMENDATION_FEATURES], dtype=float)
    )[0]

    distances = np.linalg.norm(get_scaled_dataset_vectors()[rows] - target_vector, axis=1)
    typical_distance = max(float(np.median(distances)), 1e-9)
    audio_fit = np.clip(1 - distances / typical_distance, 0, 1)

    codes, genre_names = get_genre_codes()
    affinity_by_code = np.array([genre_affinity.get(name, 0.0) for name in genre_names] + [0.0])
    genre_fit = affinity_by_code[codes[rows]]   # code -1 (no genre) picks the trailing 0.0

    weights = weights or (FIT_WEIGHTS if genre_affinity else FIT_WEIGHTS_WITHOUT_GENRES)

    scores = (
        weights["audio"] * audio_fit
        + weights["genre"] * genre_fit
        + weights["popularity"] * get_popularity_fit()[rows]
        + weights.get("raw_popularity", 0) * get_raw_popularity()[rows]
    )

    return np.clip(scores, 0, 1)


# How many of the best songs from each fitting genre are always considered
PER_GENRE_CANDIDATES = 30


def get_best_per_genre(
    scores: np.ndarray,
    allowed: np.ndarray,
    genre_affinity: dict[str, float],
    per_genre: int,
) -> np.ndarray:
    """Positions (in `scores`) of the top `per_genre` songs of each genre in genre_affinity."""
    codes, genre_names = get_genre_codes()
    allowed_codes = codes[allowed]
    picks = []

    for code, name in enumerate(genre_names):
        if genre_affinity.get(name, 0) <= 0:
            continue

        in_genre = np.flatnonzero(allowed_codes == code)

        if in_genre.size == 0:
            continue

        take = min(per_genre, in_genre.size)
        picks.append(in_genre[np.argpartition(scores[in_genre], -take)[-take:]])

    return np.concatenate(picks) if picks else np.array([], dtype=int)


def get_candidates(
    target_features: dict[str, float],
    filters: RecommendationFilters | None,
    count: int,
    exclude_ids: set[str] | None = None,
    genre_affinity: dict[str, float] | None = None,
    exclude_artists: list[str] | None = None,
    fit_weights: dict[str, float] | None = None,
    languages: list[str] | None = None,
) -> tuple[list[Track], dict[str, float]]:
    """The `count` dataset songs that fit the mood best and pass the filters,
    with their scores ({track_id: score}). Songs in exclude_ids, songs by
    exclude_artists, and songs not in `languages` (None for any) are left out."""
    dataset = load_dataset()

    mask = get_filter_mask(filters)

    if exclude_ids:
        mask &= ~dataset.index.isin(list(exclude_ids))

    if exclude_artists:
        _, artists = get_normalized_names()
        mask &= ~np.isin(artists, [normalize_name(artist) for artist in exclude_artists])

    if languages:
        mask &= get_language_mask(set(languages))

    allowed = np.flatnonzero(mask)

    if allowed.size == 0:
        return [], {}

    scores = get_fit_scores(target_features, genre_affinity or {}, allowed, fit_weights)

    # The top `count` scores, without sorting the rest (rank_tracks() sorts these)
    count = min(count, allowed.size)
    best = np.argpartition(scores, -count)[-count:]

    # Plus the best few of every fitting genre. Otherwise the genre that fits
    # best can fill the whole shortlist, and rank_tracks() has nothing else to
    # mix in.
    if genre_affinity:
        best = np.union1d(best, get_best_per_genre(scores, allowed, genre_affinity, PER_GENRE_CANDIDATES))

    rows = dataset.iloc[allowed[best]]

    tracks = [
        create_track(track_id, row)
        for track_id, row in zip(rows.index, rows.itertuples(index=False))
    ]

    track_scores = {
        track.id: round(float(score), 4)
        for track, score in zip(tracks, scores[best])
    }

    return tracks, track_scores


def create_track(track_id: str, row) -> Track:
    """A Track from one dataset row (a namedtuple from DataFrame.itertuples())."""
    return Track(
        id=track_id,
        title=row.track_name,
        artists=[row.artist_name],
        spotify_url=f"https://open.spotify.com/track/{track_id}",
        genre=row.genre,
        popularity=int(row.popularity),
        release_year=int(row.year),
        duration_ms=None if pd.isna(row.duration_ms) else int(row.duration_ms),
    )


def get_dataset_tracks(track_ids: list[str]) -> list[Track]:
    """Tracks for these IDs from the dataset; IDs it doesn't have are left out."""
    dataset = load_dataset()
    rows = dataset.loc[dataset.index.intersection(track_ids)]

    return [
        create_track(track_id, row)
        for track_id, row in zip(rows.index, rows.itertuples(index=False))
    ]


def recommend_tracks(
    target_features: dict[str, float],
    preferred_genres: list[str] | None = None,
    filters: RecommendationFilters | None = None,
    limit: int = 10,
    max_per_artist: int | None = None,
    spotify: spotipy.Spotify | None = None,
    exclude_ids: set[str] | None = None,
    taken: list[Track] | None = None,
    genre_affinity: dict[str, float] | None = None,
    featured_artists: list[str] | None = None,
    artist_share: float = 0.0,
    year_range: tuple[int, int] | None = None,
    languages: list[str] | None = None,
    fit_profile: str | None = None,
) -> list[RecommendedTrack]:
    """Songs from the dataset that fit the mood best, best match first.

    target_features   – what the songs should sound like, e.g. from interpret_mood()
    preferred_genres  – genres to look in first (e.g. "fairytale" -> classical, opera).
                        The user's own genre filter wins, and if these genres leave
                        no songs, any genre is used.
    exclude_ids       – songs never to return (e.g. ones the user removed)
    genre_affinity    – how well each genre suits the mood, 0–1 (get_genre_affinity());
                        songs in fitting genres rank higher
    taken             – songs already in the playlist: never returned, other
                        versions of them are skipped, and their artists count
                        toward max_per_artist (for finding replacements)
    featured_artists  – artists the user named; artist_share (0–1) of the playlist
                        (taken songs included) is their songs, the rest is
                        similar-sounding songs by other artists, mixed in between
    year_range        – (first, last) release year the user asked for, unless the
                        filters set years. If no songs match, any year is used.
                        Popular songs of the time count more (ERA_WEIGHTS).
    languages         – languages the songs may be in (see language.py); None for any.
                        Songs by featured artists are exempt. If no songs pass,
                        any language is used.

    Each song comes with its similarity score, audio features, and, where they
    can be found, its album and album artwork. Those come from Spotify when the
    user is logged in (`spotify`), otherwise only the artwork is looked up.

    Raises DatasetUnavailableError if the dataset isn't downloaded.
    """
    if load_dataset() is None:
        raise DatasetUnavailableError

    taken = taken or []
    weights = FIT_PROFILES.get(fit_profile) or (ERA_WEIGHTS if year_range else None)

    def recommend(with_filters):
        featured_songs = []

        if featured_artists and artist_share > 0:
            count = get_featured_count(featured_artists, artist_share, limit, taken)

            if count:
                featured_songs = find_featured_songs(
                    featured_artists, count, target_features, with_filters, spotify,
                    exclude_ids, taken, genre_affinity, artist_only=artist_share >= 1,
                )

        others = []
        remaining = limit - len(featured_songs)

        if remaining > 0:
            others = find_with_preferred_genres(
                target_features, preferred_genres, with_filters, remaining, max_per_artist, spotify,
                exclude_ids, [*taken, *featured_songs], genre_affinity, exclude_artists=featured_artists,
                fit_weights=weights, languages=languages,
            )

        return interleave(featured_songs, others)

    # Years the user asked for ("2010s"), unless the filters already set years
    if year_range and not (filters and (filters.min_year or filters.max_year)):
        with_years = (filters or RecommendationFilters()).model_copy(
            update={"min_year": year_range[0], "max_year": year_range[1]}
        )
        results = recommend(with_years)

        if results:
            return results

    results = recommend(filters)

    # Nothing in those languages: any language is better than nothing
    if not results and languages:
        return recommend_tracks(
            target_features, preferred_genres, filters, limit, max_per_artist, spotify, exclude_ids,
            taken, genre_affinity, featured_artists, artist_share, year_range, languages=None,
            fit_profile=fit_profile,
        )

    return results


def find_with_preferred_genres(
    target_features, preferred_genres, filters, limit, max_per_artist, spotify,
    exclude_ids, taken, genre_affinity, exclude_artists=None, fit_weights=None, languages=None,
) -> list[RecommendedTrack]:
    """find_tracks() in the preferred genres first, then in any genre if they leave nothing.
    The user's own genre filter wins over preferred genres."""
    if preferred_genres and not (filters and filters.genres):
        with_genres = (filters or RecommendationFilters()).model_copy(update={"genres": preferred_genres})
        results = find_tracks(
            target_features, with_genres, limit, max_per_artist, spotify,
            exclude_ids, taken, genre_affinity, exclude_artists, fit_weights, languages,
        )

        if results:
            return results

    return find_tracks(
        target_features, filters, limit, max_per_artist, spotify,
        exclude_ids, taken, genre_affinity, exclude_artists, fit_weights, languages,
    )


def get_featured_count(
    featured_artists: list[str],
    artist_share: float,
    limit: int,
    taken: list[Track],
) -> int:
    """How many of the `limit` new songs should be by the featured artists, so
    that artist_share of the whole playlist (taken songs included) is theirs."""
    names = {normalize_name(artist) for artist in featured_artists}
    already = sum(
        1 for track in taken
        if any(normalize_name(artist) in names for artist in track.artists)
    )
    wanted = math.ceil(artist_share * (len(taken) + limit))

    return max(0, min(limit, wanted - already))


def find_featured_songs(
    featured_artists, count, target_features, filters, spotify,
    exclude_ids, taken, genre_affinity, artist_only,
) -> list[RecommendedTrack]:
    """Songs by the artists the user named, best fitting first. With several
    artists, each gets a fair share. On its own ("taylor swift"), their
    best-known songs come first."""
    with_artists = (filters or RecommendationFilters()).model_copy(
        update={"artists": featured_artists, "genres": None}
    )
    per_artist = None if len(featured_artists) == 1 else math.ceil(count / len(featured_artists))

    songs = find_tracks(
        target_features, with_artists, count, per_artist, spotify, exclude_ids, taken,
        genre_affinity, fit_weights=ARTIST_ONLY_WEIGHTS if artist_only else None,
    )

    # They're by the artist asked for, so that part of the description is matched
    return [
        song.model_copy(update={"score": round(ARTIST_MATCH_CREDIT + (1 - ARTIST_MATCH_CREDIT) * song.score, 4)})
        for song in songs
    ]


def interleave(first: list[RecommendedTrack], second: list[RecommendedTrack]) -> list[RecommendedTrack]:
    """[a1, b1, a2, b2, ...], then whatever is left of the longer list."""
    mixed = []

    for index in range(max(len(first), len(second))):
        if index < len(first):
            mixed.append(first[index])
        if index < len(second):
            mixed.append(second[index])

    return mixed


def find_tracks(
    target_features: dict[str, float],
    filters: RecommendationFilters | None,
    limit: int,
    max_per_artist: int | None,
    spotify: spotipy.Spotify | None,
    exclude_ids: set[str] | None = None,
    taken: list[Track] | None = None,
    genre_affinity: dict[str, float] | None = None,
    exclude_artists: list[str] | None = None,
    fit_weights: dict[str, float] | None = None,
    languages: list[str] | None = None,
) -> list[RecommendedTrack]:
    """The best `limit` songs for one set of filters, with details filled in."""
    taken = taken or []
    exclude_ids = (exclude_ids or set()) | {track.id for track in taken}

    # Room for the candidates rank_tracks() will skip because they clash with taken songs
    count = (limit + len(taken)) * CANDIDATES_PER_RESULT
    tracks, scores = get_candidates(
        target_features, filters, count, exclude_ids, genre_affinity, exclude_artists, fit_weights, languages,
    )

    filtering_explicit = filters is not None and not filters.allow_explicit
    detail_count = limit * EXPLICIT_FILTER_HEADROOM if filtering_explicit else limit

    ranked = rank_tracks(tracks, scores, limit=detail_count, max_per_artist=max_per_artist, taken=taken)
    ranked = add_track_details(ranked, spotify)

    # The details from Spotify include the explicit flag, so the filters are
    # checked again now. The other filters already passed and still do.
    ranked = filter_tracks(ranked, filters)[:limit]

    features = get_dataset_features([track.id for track in ranked])

    return [
        track.model_copy(update={"audio_features": features[track.id]})
        for track in ranked
    ]
