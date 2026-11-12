import spotipy

from app.models.track import Track


def get_release_year(release_date: str | None) -> int | None:
    # Spotify gives "2019-11-29", "2019-11", or just "2019"
    if not release_date or not release_date[:4].isdigit():
        return None

    return int(release_date[:4])


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
            spotify_url=item["external_urls"]["spotify"],
            explicit=item.get("explicit"),
            popularity=item.get("popularity"),
            release_year=get_release_year(item["album"].get("release_date")),
        ))

    return tracks
