from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.models.audio_features import AudioFeatures
from app.models.playlist import TrackId
from app.models.track import Track

MIN_MOOD_LENGTH = 3
MAX_MOOD_LENGTH = 500


# A genre or artist name: surrounding spaces removed, can't be empty
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class RecommendationFilters(BaseModel):
    # Every filter is optional. One that is left out doesn't restrict anything.
    genres: list[Name] | None = Field(
        None,
        max_length=20,
        description="Only tracks in one of these genres",
        examples=[["indie-pop", "folk"]],
    )
    artists: list[Name] | None = Field(
        None,
        max_length=20,
        description="Only tracks by one of these artists",
        examples=[["Phoebe Bridgers"]],
    )
    allow_explicit: bool = Field(
        True,
        description="Set to false to leave out explicit tracks",
    )
    min_popularity: int | None = Field(None, ge=0, le=100, description="Least popular allowed (0–100)")
    max_popularity: int | None = Field(None, ge=0, le=100, description="Most popular allowed (0–100)")
    min_year: int | None = Field(None, ge=1900, le=2100, description="Earliest release year allowed")
    max_year: int | None = Field(None, ge=1900, le=2100, description="Latest release year allowed")

    @model_validator(mode="after")
    def ranges_must_be_in_order(self):
        if (
            self.min_popularity is not None
            and self.max_popularity is not None
            and self.min_popularity > self.max_popularity
        ):
            raise ValueError("min_popularity cannot be greater than max_popularity.")

        if (
            self.min_year is not None
            and self.max_year is not None
            and self.min_year > self.max_year
        ):
            raise ValueError("min_year cannot be greater than max_year.")

        return self


# How much of a feature a song should have, as picked by the in-browser AI.
# services/mood_interpretation.py turns these into numbers.
Level = Literal["very_low", "low", "medium", "high", "very_high"]
TempoLevel = Literal["very_slow", "slow", "medium", "fast", "very_fast"]

MoodWord = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=40)]


class Vibe(BaseModel):
    """The in-browser AI's reading of the mood description (frontend/js/vibe-ai.js).

    Optional: without it, the backend understands the description with its own
    word lists. With it, niche descriptions the word lists don't know still work.
    """
    moods: list[MoodWord] = Field(..., min_length=1, max_length=6, examples=[["nostalgic", "late night", "city drive"]])
    energy: Level
    valence: Level         # sad (very_low) to happy (very_high)
    tempo: TempoLevel
    acousticness: Level
    danceability: Level
    instrumentalness: Level
    genres: list[Name] = Field(default_factory=list, max_length=5)
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None


class RecommendationRequest(BaseModel):
    # The user's mood or situation in their own words,
    # e.g. "rainy Sunday morning, studying with coffee"
    mood: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,  # surrounding spaces don't count toward the length
            min_length=MIN_MOOD_LENGTH,
            max_length=MAX_MOOD_LENGTH,
        ),
    ] = Field(
        ...,
        description="Natural-language description of a mood or situation",
        examples=["rainy Sunday morning, studying with coffee"],
    )

    # Optional preferences that narrow down which songs can be recommended
    filters: RecommendationFilters | None = None

    # Optional reading of the mood by the in-browser AI, see Vibe
    vibe: Vibe | None = None

    limit: int = Field(10, ge=1, le=50, description="How many songs to return")
    max_per_artist: int | None = Field(
        2,
        ge=1,
        description="Most songs by one artist; null for no limit",
    )

    @field_validator("mood")
    @classmethod
    def mood_must_contain_words(cls, value: str) -> str:
        # Reject input like "!!!" or "12345" that has nothing to interpret
        if not any(character.isalpha() for character in value):
            raise ValueError("Mood description must contain at least one letter.")

        # Collapse repeated spaces and line breaks into single spaces
        return " ".join(value.split())


class RecommendedTrack(Track):
    score: float  # similarity to the mood, 0–1; higher is a better match
    # The song's tempo, energy, mood, etc. Always filled in by POST /recommendations.
    audio_features: AudioFeatures | None = None


class RecommendationResponse(BaseModel):
    mood: str                     # the cleaned-up description that was used
    mood_terms: list[str]         # what Vibely understood, e.g. ["rainy", "calm"]
    understood_by: Literal["ai", "keywords"]  # "ai" if a vibe was sent, otherwise the word lists
    target_features: dict[str, float]  # audio features the songs should be close to
    preferred_genres: list[str]   # genres looked in first, e.g. ["classical", "opera"]; often empty
    genre_affinity: dict[str, float]  # how well each genre suits the mood, 0–1, e.g. {"folk": 1.0, "jazz": 0.5}
    notes: list[str] = []         # things Vibely couldn't do, e.g. "no songs from the 1990s"
    playlist_title: str           # suggested playlist name, e.g. "Rainy Morning Focus"
    recommendations: list[RecommendedTrack]  # songs matching the mood, best first


class MoreRecommendationsRequest(BaseModel):
    """More songs for the same description, e.g. to replace ones the user removed.

    Send the same mood (and vibe, if the AI read it) as the /recommendations
    request, so the new songs fit the same mood, artists, genres, and years.
    The AI isn't run again: the backend works the mood out from the vibe given.
    """
    mood: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=MIN_MOOD_LENGTH, max_length=MAX_MOOD_LENGTH),
    ]
    vibe: Vibe | None = None
    filters: RecommendationFilters | None = None

    playlist_ids: list[TrackId] = Field(
        default_factory=list,
        max_length=500,
        description="Songs in the playlist now: not returned again, nor other versions of them, "
                    "and their artists count toward max_per_artist",
    )
    exclude_ids: list[TrackId] = Field(
        default_factory=list,
        max_length=1000,
        description="Other songs never to return, e.g. ones the user removed",
    )

    limit: int = Field(1, ge=1, le=20, description="How many new songs to return")
    max_per_artist: int | None = Field(2, ge=1, description="Most songs by one artist in the whole playlist; null for no limit")


class MoreRecommendationsResponse(BaseModel):
    recommendations: list[RecommendedTrack]  # new songs, best match first; empty if none are left
