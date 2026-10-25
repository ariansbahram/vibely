from pydantic import BaseModel


class Track(BaseModel):
    id: str               # Spotify track ID, used later to add songs to playlists
    title: str
    artists: list[str]    # a song can have several artists
    album: str
    spotify_url: str      # link that opens the song in Spotify
