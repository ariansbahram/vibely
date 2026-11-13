import math
import re
from collections import Counter

from app.models.recommendation import RecommendedTrack
from app.models.track import Track


# At most this share of the playlist from one genre, so a mood like "studying"
# doesn't come back as ten lo-fi tracks. If that leaves the playlist short
# (e.g. a mood limited to one genre), the rest is filled without the limit.
MAX_GENRE_SHARE = 0.4


def normalize_title(title: str) -> str:
    """Reduce a title to its core so different versions of a song look the same.

    "Blinding Lights - Remastered" and "Blinding Lights (Live)" -> "blinding lights"
    """
    text = title.lower()
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", text)  # drop "(feat. ...)", "[Live]", etc.
    text = text.split(" - ")[0]                   # drop " - Remastered 2011", etc.
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()

    # A title that is only brackets or symbols, e.g. "(Intro)", would end up empty
    return text or title.lower().strip()


def get_song_key(track: Track) -> tuple[str, str]:
    """Same title and same main artist means the same song, even if the IDs differ
    (single vs. album version, remaster, live recording)."""
    main_artist = track.artists[0].lower().strip() if track.artists else ""

    return (normalize_title(track.title), main_artist)


def rank_tracks(
    tracks: list[Track],
    scores: dict[str, float],
    limit: int = 10,
    max_per_artist: int | None = None,
    taken: list[Track] | None = None,
) -> list[RecommendedTrack]:
    """Return the top matching tracks, best first.

    tracks          – candidate tracks, in any order
    scores          – {track_id: similarity score}, e.g. from score_tracks().
                      Tracks without a score are left out.
    limit           – how many tracks to return at most
    max_per_artist  – how many tracks one artist may appear on;
                      None means no restriction

    taken           – songs already in the playlist (when finding replacements):
                      other versions of them are skipped, and their artists count
                      toward max_per_artist

    Duplicates are removed: a track ID is used once, and so is each song
    (same title and main artist). The highest-scoring version is the one kept.

    For variety, one genre fills at most MAX_GENRE_SHARE of the playlist
    (taken songs included) unless there aren't enough other songs.
    """
    scored_tracks = [track for track in tracks if track.id in scores]
    scored_tracks.sort(key=lambda track: scores[track.id], reverse=True)

    taken = taken or []

    ranked = []
    seen_ids = {track.id for track in taken}
    seen_songs = {get_song_key(track) for track in taken}
    artist_counts = Counter(
        artist.lower().strip()
        for track in taken
        for artist in track.artists
    )
    genre_counts = Counter(track.genre for track in taken if track.genre)
    max_per_genre = max(1, math.ceil(MAX_GENRE_SHARE * (len(taken) + limit)))

    # First pass with the genre limit, second without it to fill any gap
    for limit_genres in (True, False):
        for track in scored_tracks:
            if len(ranked) >= limit:
                break

            song_key = get_song_key(track)

            if track.id in seen_ids or song_key in seen_songs:
                continue

            artists = {artist.lower().strip() for artist in track.artists}

            if max_per_artist is not None and any(
                artist_counts[artist] >= max_per_artist for artist in artists
            ):
                continue

            if limit_genres and track.genre and genre_counts[track.genre] >= max_per_genre:
                continue

            seen_ids.add(track.id)
            seen_songs.add(song_key)
            artist_counts.update(artists)
            genre_counts[track.genre] += 1

            ranked.append(
                RecommendedTrack(**track.model_dump(), score=scores[track.id])
            )

    # The second pass may add lower-scoring songs after higher ones; keep best first
    ranked.sort(key=lambda track: track.score, reverse=True)
    return ranked
