from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

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

    @field_validator("mood")
    @classmethod
    def mood_must_contain_words(cls, value: str) -> str:
        # Reject input like "!!!" or "12345" that has nothing to interpret
        if not any(character.isalpha() for character in value):
            raise ValueError("Mood description must contain at least one letter.")

        # Collapse repeated spaces and line breaks into single spaces
        return " ".join(value.split())


class RecommendedTrack(Track):
    score: float  # similarity to the mood; higher is a better match


class RecommendationResponse(BaseModel):
    mood: str                     # the cleaned-up description that was used
    mood_terms: list[str]         # meaningful terms found in it, e.g. ["rainy", "calm"]
    target_features: dict[str, float]  # audio features the songs should be close to
    recommendations: list[RecommendedTrack]  # songs matching the mood, best first
