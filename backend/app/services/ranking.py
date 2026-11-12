import re
from collections import Counter

from app.models.recommendation import RecommendedTrack
from app.models.track import Track


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
) -> list[RecommendedTrack]:
    """Return the top matching tracks, best first.

    tracks          – candidate tracks, in any order
    scores          – {track_id: similarity score}, e.g. from score_tracks().
                      Tracks without a score are left out.
    limit           – how many tracks to return at most
    max_per_artist  – how many tracks one artist may appear on;
                      None means no restriction

    Duplicates are removed: a track ID is used once, and so is each song
    (same title and main artist). The highest-scoring version is the one kept.
    """
    scored_tracks = [track for track in tracks if track.id in scores]
    scored_tracks.sort(key=lambda track: scores[track.id], reverse=True)

    ranked = []
    seen_ids = set()
    seen_songs = set()
    artist_counts = Counter()

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

        seen_ids.add(track.id)
        seen_songs.add(song_key)
        artist_counts.update(artists)

        ranked.append(
            RecommendedTrack(**track.model_dump(), score=scores[track.id])
        )

    return ranked
