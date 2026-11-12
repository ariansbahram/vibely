import re

from app.models.recommendation import RecommendationFilters
from app.models.track import Track


def normalize_name(name: str) -> str:
    """Make names comparable: "Hip Hop", "hip-hop" and " HIP_HOP " are the same."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def matches_filters(track: Track, filters: RecommendationFilters) -> bool:
    """True if the track passes every filter that is set.

    A track that is missing the detail a filter needs does not pass it:
    with a genre filter set, a track of unknown genre is left out.
    """
    if filters.genres:  # an empty list means no genre filter
        allowed_genres = {normalize_name(genre) for genre in filters.genres}

        if track.genre is None or normalize_name(track.genre) not in allowed_genres:
            return False

    if filters.artists:  # an empty list means no artist filter
        allowed_artists = {normalize_name(artist) for artist in filters.artists}
        track_artists = {normalize_name(artist) for artist in track.artists}

        # One matching artist is enough, so featured appearances count
        if not allowed_artists & track_artists:
            return False

    if not filters.allow_explicit:
        # Only tracks known to be clean pass; unknown is treated as possibly explicit
        if track.explicit is not False:
            return False

    if filters.min_popularity is not None or filters.max_popularity is not None:
        if track.popularity is None:
            return False

        if filters.min_popularity is not None and track.popularity < filters.min_popularity:
            return False

        if filters.max_popularity is not None and track.popularity > filters.max_popularity:
            return False

    if filters.min_year is not None or filters.max_year is not None:
        if track.release_year is None:
            return False

        if filters.min_year is not None and track.release_year < filters.min_year:
            return False

        if filters.max_year is not None and track.release_year > filters.max_year:
            return False

    return True


def filter_tracks(
    tracks: list[Track],
    filters: RecommendationFilters | None = None,
) -> list[Track]:
    """Keep only the tracks that match the user's preferences, in the same order.

    With no filters, every track is kept.
    """
    if filters is None:
        return list(tracks)

    return [track for track in tracks if matches_filters(track, filters)]
