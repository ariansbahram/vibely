from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# A Spotify track ID: 22 letters and digits, e.g. "0VjIjW4GlUZAMYd2vXMi3b"
TrackId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9]{22}$")]

MAX_TRACKS = 500


class PlaylistRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(..., description="Playlist name", examples=["Vibely: rainy Sunday morning"])

    description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, max_length=300),  # Spotify's limit
    ] = Field("", description="Shown under the name in Spotify")

    track_ids: list[TrackId] = Field(
        ...,
        min_length=1,
        max_length=MAX_TRACKS,
        description="Spotify track IDs, in playlist order (e.g. the `id` of each recommendation)",
        examples=[["0VjIjW4GlUZAMYd2vXMi3b"]],
    )

    public: bool = Field(False, description="Show the playlist on the user's Spotify profile")


class PlaylistResponse(BaseModel):
    id: str              # Spotify playlist ID
    name: str
    spotify_url: str     # link that opens the playlist in Spotify
    track_count: int     # songs added (duplicates in the request are added once)
