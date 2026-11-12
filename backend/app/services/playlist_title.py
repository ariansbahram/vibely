"""Suggest a playlist title from a mood description.

The title is built from the mood terms found by extract_mood_terms():
  "rainy Sunday morning, studying with coffee" -> "Rainy Morning Focus"
  "nostalgic late-night drive in the rain"     -> "Nostalgic Late Night Road Trip"
  "sad and lonely"                             -> "Sad & Lonely Vibes"
  "studying"                                   -> "Focus Mix"
"""

# How each mood term appears in a title, by its role:
#   describe – how it feels ("Rainy", "Nostalgic"), comes first
#   when     – time of day ("Morning"), comes in the middle
#   what     – what it's for ("Focus", "Road Trip"), comes last
DESCRIBE_WORDS = {
    "happy": "Happy",
    "sad": "Sad",
    "melancholic": "Melancholy",
    "heartbroken": "Heartbroken",
    "lonely": "Lonely",
    "angry": "Angry",
    "anxious": "Restless",
    "romantic": "Romantic",
    "nostalgic": "Nostalgic",
    "hopeful": "Hopeful",
    "confident": "Confident",
    "dreamy": "Dreamy",
    "dark": "Dark",
    "energetic": "High Energy",
    "upbeat": "Upbeat",
    "calm": "Calm",
    "chill": "Chill",
    "sleepy": "Sleepy",
    "rainy": "Rainy",
    "sunny": "Sunny",
    "cozy": "Cozy",
}

WHEN_WORDS = {
    "late night": "Late Night",
    "morning": "Morning",
}

WHAT_WORDS = {
    "focused": "Focus",
    "workout": "Workout",
    "party": "Party",
    "road trip": "Road Trip",
}

# Ends a title that has no "what" word: "Rainy Morning" -> "Rainy Morning Vibes"
DEFAULT_ENDING = "Vibes"

# Added after a "what" word that would otherwise stand alone: "Focus" -> "Focus Mix"
LONE_WHAT_ENDING = "Mix"

# With more describe words than this, only the first ones are used, so titles stay short
MAX_DESCRIBE_WORDS = 2

MAX_TITLE_LENGTH = 100  # Spotify's limit for playlist names

# For a description with no known mood terms, at most this much of it is used
MAX_FALLBACK_LENGTH = 50


def generate_playlist_title(mood: str, mood_terms: list[str]) -> str:
    """A short playlist title for a mood description.

    mood        – the user's description, as sent to /recommendations
    mood_terms  – the terms extract_mood_terms() found in it, in order
    """
    describe = [DESCRIBE_WORDS[term] for term in mood_terms if term in DESCRIBE_WORDS]
    when = [WHEN_WORDS[term] for term in mood_terms if term in WHEN_WORDS]
    what = [WHAT_WORDS[term] for term in mood_terms if term in WHAT_WORDS]

    if not (describe or when or what):
        return title_from_description(mood)

    # With a time or activity, one describe word is enough ("Rainy Morning Focus");
    # on their own, two read well joined with "&" ("Sad & Lonely Vibes")
    if when or what:
        describe = describe[:1]
        describing = describe
    else:
        describe = describe[:MAX_DESCRIBE_WORDS]
        describing = [" & ".join(describe)] if describe else []

    parts = [*describing, *when[:1], what[0] if what else DEFAULT_ENDING]

    if len(parts) == 1:
        parts.append(LONE_WHAT_ENDING)

    return " ".join(parts)[:MAX_TITLE_LENGTH]


def title_from_description(mood: str) -> str:
    """The description itself, shortened at a word break and capitalized."""
    text = mood.strip()

    if len(text) > MAX_FALLBACK_LENGTH:
        text = text[:MAX_FALLBACK_LENGTH].rsplit(" ", 1)[0].rstrip(",.;:-") + "…"

    return text[:1].upper() + text[1:]
