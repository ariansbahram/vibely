from pydantic import BaseModel


class AudioFeatures(BaseModel):
    track_id: str            # Spotify track ID, matches Track.id
    acousticness: float      # 0–1, how acoustic (vs. electronic)
    danceability: float      # 0–1, how danceable
    energy: float            # 0–1, how intense/active
    instrumentalness: float  # 0–1, how likely there are no vocals
    liveness: float          # 0–1, how likely it's a live recording
    loudness: float          # in decibels, usually -60 to 0
    speechiness: float       # 0–1, how much spoken word
    tempo: float             # beats per minute
    valence: float           # 0–1, sad (0) to happy (1)
    key: int                 # 0 = C, 1 = C#, ... 11 = B
    mode: int                # 1 = major, 0 = minor
