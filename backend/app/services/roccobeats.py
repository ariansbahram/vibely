import requests

from app.models.audio_features import AudioFeatures

RECCOBEATS_URL = "https://api.reccobeats.com/v1/audio-features"
MAX_IDS_PER_REQUEST = 40   # ReccoBeats rejects more than 40 IDs per request


def get_audio_features(track_ids: list[str]):
    track_ids = list(dict.fromkeys(track_ids))   # remove duplicates, keep order
    features = {}

    for start in range(0, len(track_ids), MAX_IDS_PER_REQUEST):
        batch = track_ids[start:start + MAX_IDS_PER_REQUEST]

        try:
            response = requests.get(
                RECCOBEATS_URL,
                params={"ids": ",".join(batch)},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue   # ReccoBeats is down or rate-limited; these tracks stay missing

        for item in response.json().get("content", []):
            track_id = item["href"].rsplit("/", 1)[-1]
            features[track_id] = AudioFeatures(track_id=track_id, **item)

    return features


RECCOBEATS_API = "https://api.reccobeats.com/v1"


def get_json(path: str, params: dict) -> dict | None:
    """GET a ReccoBeats endpoint; None if it fails (down, rate-limited, slow)."""
    try:
        response = requests.get(f"{RECCOBEATS_API}/{path}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def search_artists(name: str, size: int = 10) -> list[dict]:
    """Artists matching a name: [{"id", "name", "href" (Spotify link)}]. Several can share a name."""
    reply = get_json("artist/search", {"searchText": name, "size": size})
    return reply.get("content", []) if reply else []


def get_artist_tracks(artist_id: str, size: int = 25) -> list[dict]:
    """Tracks by a ReccoBeats artist: [{"trackTitle", "artists", "href", "popularity", ...}]."""
    reply = get_json(f"artist/{artist_id}/track", {"size": size})
    return reply.get("content", []) if reply else []


def search_tracks(text: str, size: int = 10) -> list[dict]:
    """Tracks matching a title (and maybe artist): same fields as get_artist_tracks()."""
    reply = get_json("track/search", {"searchText": text, "size": size})
    return reply.get("content", []) if reply else []


def spotify_id(href: str) -> str:
    """"https://open.spotify.com/track/1BxfuPKGuaTgP7aM0Bbdwr" -> "1BxfuPKGuaTgP7aM0Bbdwr"."""
    return href.rstrip("/").rsplit("/", 1)[-1]
