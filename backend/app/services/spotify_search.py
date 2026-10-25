import spotipy

from app.models.track import Track


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
        ))

    return tracks
