from pydantic import BaseModel


class Track(BaseModel):
    id: str               # Spotify track ID, used later to add songs to playlists
    title: str
    artists: list[str]    # a song can have several artists
    album: str | None = None           # None when the source doesn't say (the dataset has no albums)
    album_image_url: str | None = None  # album artwork; None if it couldn't be found
    spotify_url: str      # link that opens the song in Spotify

    # Extra details used by the recommendation filters.
    # None means the source the track came from doesn't provide that detail.
    genre: str | None = None         # e.g. "hip-hop" (from the dataset; Spotify search has no genre)
    explicit: bool | None = None     # True if marked explicit (from Spotify; the dataset has no flag)
    popularity: int | None = None    # 0–100, higher is more popular
    release_year: int | None = None  # e.g. 2019
    duration_ms: int | None = None   # song length in milliseconds
