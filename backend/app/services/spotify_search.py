import spotipy

from app.models.track import Track


def get_release_year(release_date: str | None) -> int | None:
    # Spotify gives "2019-11-29", "2019-11", or just "2019"
    if not release_date or not release_date[:4].isdigit():
        return None

    return int(release_date[:4])


def get_album_image_url(album: dict) -> str | None:
    # Spotify lists the artwork in several sizes, largest first (usually 640, 300, 64 px)
    images = album.get("images") or []

    return images[0]["url"] if images else None


def search_tracks(spotify: spotipy.Spotify, query: str, limit: int = 10):
    results = spotify.search(q=query, type="track", limit=limit)

    tracks = []
    for item in results["tracks"]["items"]:
        if not item:
            continue

        tracks.append(Track(
            id=item["id"],
            title=item["name"],
            artists=[artist["name"] for artist in item["artists"]],
            album=item["album"]["name"],
            album_image_url=get_album_image_url(item["album"]),
            spotify_url=item["external_urls"]["spotify"],
            explicit=item.get("explicit"),
            popularity=item.get("popularity"),
            release_year=get_release_year(item["album"].get("release_date")),
            duration_ms=item.get("duration_ms"),
        ))

    return tracks
