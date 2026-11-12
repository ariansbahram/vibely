from concurrent.futures import ThreadPoolExecutor

import requests
import spotipy

from app.models.track import Track
from app.services.spotify_search import get_album_image_url

MAX_IDS_PER_SPOTIFY_REQUEST = 50  # Spotify's limit for looking up several tracks at once

# Spotify's public embed info: gives a song's artwork without logging in
OEMBED_URL = "https://open.spotify.com/oembed"
OEMBED_WORKERS = 10

# Artwork found through oEmbed, so a song is only looked up once: {track_id: url}
_artwork_cache: dict[str, str] = {}


def get_spotify_details(spotify: spotipy.Spotify, track_ids: list[str]) -> dict[str, dict]:
    """Album name, artwork, and explicit flag from Spotify: {track_id: {...}}.

    A song Spotify couldn't return is left out, so its artwork is looked up another way.
    """
    details = {}

    for start in range(0, len(track_ids), MAX_IDS_PER_SPOTIFY_REQUEST):
        batch = track_ids[start:start + MAX_IDS_PER_SPOTIFY_REQUEST]

        try:
            items = spotify.tracks(batch)["tracks"]
        except (spotipy.SpotifyException, requests.RequestException):
            continue  # Spotify is down or rate-limited; try oEmbed for these songs

        for item in items:
            if not item:
                continue

            details[item["id"]] = {
                "album": item["album"]["name"],
                "album_image_url": get_album_image_url(item["album"]),
                "explicit": item.get("explicit"),
            }

    return details


def get_oembed_artwork(spotify_url: str) -> str | None:
    try:
        response = requests.get(OEMBED_URL, params={"url": spotify_url}, timeout=5)
        response.raise_for_status()
    except requests.RequestException:
        return None

    return response.json().get("thumbnail_url")


def get_artwork_without_login(tracks: list[Track]) -> dict[str, str]:
    """Album artwork for each song through oEmbed: {track_id: url}. Songs without any are left out."""
    to_fetch = [track for track in tracks if track.id not in _artwork_cache]

    with ThreadPoolExecutor(max_workers=OEMBED_WORKERS) as pool:
        urls = pool.map(lambda track: get_oembed_artwork(track.spotify_url), to_fetch)

        for track, url in zip(to_fetch, urls):
            if url:
                _artwork_cache[track.id] = url  # failures aren't cached, so they're retried next time

    return {track.id: _artwork_cache[track.id] for track in tracks if track.id in _artwork_cache}


def add_track_details(tracks: list[Track], spotify: spotipy.Spotify | None = None) -> list[Track]:
    """The same tracks with album, album artwork, and explicit flag filled in where possible.

    Logged in (`spotify` given): all three come from Spotify.
    Otherwise, or for songs Spotify didn't return, only the artwork is looked up (via oEmbed).
    """
    details = get_spotify_details(spotify, [track.id for track in tracks]) if spotify else {}

    missing = [track for track in tracks if track.id not in details]
    artwork = get_artwork_without_login(missing) if missing else {}

    return [
        track.model_copy(update=details.get(track.id, {"album_image_url": artwork.get(track.id)}))
        for track in tracks
    ]
