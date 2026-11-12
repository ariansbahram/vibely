import spotipy

from app.models.playlist import PlaylistResponse

MAX_TRACKS_PER_REQUEST = 100  # Spotify adds at most 100 songs per request


def create_playlist(
    spotify: spotipy.Spotify,
    name: str,
    track_ids: list[str],
    description: str = "",
    public: bool = False,
) -> PlaylistResponse:
    """Create a playlist in the logged-in user's Spotify account and add the songs to it.

    Songs are added in the order given; a song that appears twice is added once.
    If adding the songs fails, the new (empty) playlist is deleted again and the
    SpotifyException is raised, so the user isn't left with an empty playlist.
    """
    track_ids = list(dict.fromkeys(track_ids))  # remove duplicates, keep order

    playlist = spotify.current_user_playlist_create(
        name,
        public=public,
        description=description,
    )

    try:
        for start in range(0, len(track_ids), MAX_TRACKS_PER_REQUEST):
            spotify.playlist_add_items(
                playlist["id"],
                track_ids[start:start + MAX_TRACKS_PER_REQUEST],
            )
    except spotipy.SpotifyException:
        # Spotify has no "delete playlist"; unfollowing your own playlist removes it
        try:
            spotify.current_user_unfollow_playlist(playlist["id"])
        except spotipy.SpotifyException:
            pass  # cleanup is best effort; report the original error

        raise

    return PlaylistResponse(
        id=playlist["id"],
        name=playlist["name"],
        spotify_url=playlist["external_urls"]["spotify"],
        track_count=len(track_ids),
    )
