import numpy as np

from app.services.feature_vector import RECOMMENDATION_FEATURES

# What an "average" song looks like, close to the middle of the Kaggle dataset.
# Used for any feature the mood terms say nothing about.
NEUTRAL_TARGETS = {
    "energy": 0.65,
    "tempo": 120.0,
    "valence": 0.45,
    "acousticness": 0.30,
    "danceability": 0.55,
    "instrumentalness": 0.10,
}

# The musical characteristics each mood term points to.
# All values are 0–1 except tempo, which is in beats per minute.
# A term only lists the features it has an opinion about; "rainy" says
# nothing about danceability, so it leaves danceability alone.
MOOD_TARGETS = {
    # Feelings
    "happy": {"valence": 0.85, "energy": 0.70, "danceability": 0.70, "tempo": 120.0},
    "sad": {"valence": 0.15, "energy": 0.30, "acousticness": 0.60, "tempo": 85.0, "danceability": 0.35},
    "melancholic": {"valence": 0.25, "energy": 0.35, "acousticness": 0.55, "tempo": 90.0},
    "heartbroken": {"valence": 0.15, "energy": 0.35, "acousticness": 0.55, "tempo": 85.0},
    "lonely": {"valence": 0.20, "energy": 0.30, "acousticness": 0.60, "tempo": 85.0},
    "longing": {"valence": 0.25, "energy": 0.35, "acousticness": 0.55, "tempo": 90.0},
    "homesick": {"valence": 0.30, "energy": 0.35, "acousticness": 0.65, "tempo": 90.0},
    "grieving": {"valence": 0.10, "energy": 0.20, "acousticness": 0.75, "tempo": 75.0, "danceability": 0.25, "instrumentalness": 0.30},
    "numb": {"valence": 0.20, "energy": 0.25, "acousticness": 0.45, "tempo": 85.0, "instrumentalness": 0.35, "danceability": 0.40},
    "angry": {"valence": 0.25, "energy": 0.92, "acousticness": 0.05, "tempo": 145.0},
    "anxious": {"valence": 0.45, "energy": 0.30, "acousticness": 0.65, "tempo": 80.0, "instrumentalness": 0.40},
    "romantic": {"valence": 0.60, "energy": 0.45, "acousticness": 0.50, "tempo": 95.0, "danceability": 0.55},
    "sensual": {"valence": 0.50, "energy": 0.50, "acousticness": 0.30, "tempo": 95.0, "danceability": 0.75, "instrumentalness": 0.05},
    "nostalgic": {"valence": 0.40, "energy": 0.45, "acousticness": 0.50, "tempo": 100.0},
    "reflective": {"valence": 0.35, "energy": 0.30, "acousticness": 0.60, "tempo": 90.0, "instrumentalness": 0.30},
    "hopeful": {"valence": 0.70, "energy": 0.60, "tempo": 115.0},
    "grateful": {"valence": 0.70, "energy": 0.45, "acousticness": 0.55, "tempo": 100.0},
    "excited": {"valence": 0.80, "energy": 0.80, "tempo": 125.0, "danceability": 0.70},
    "triumphant": {"valence": 0.80, "energy": 0.85, "tempo": 125.0, "acousticness": 0.15},
    "confident": {"valence": 0.70, "energy": 0.80, "danceability": 0.75, "tempo": 115.0},
    "playful": {"valence": 0.85, "energy": 0.65, "danceability": 0.75, "tempo": 118.0},
    "rebellious": {"valence": 0.40, "energy": 0.88, "acousticness": 0.08, "tempo": 135.0},
    "epic": {"valence": 0.50, "energy": 0.75, "acousticness": 0.30, "tempo": 120.0, "instrumentalness": 0.50, "danceability": 0.40},
    # Knights, princesses, castles: sweeping and romantic, mostly acoustic/orchestral,
    # gentle rather than danceable
    "fairytale": {"valence": 0.60, "energy": 0.40, "acousticness": 0.70, "tempo": 100.0, "danceability": 0.35, "instrumentalness": 0.45},
    "mysterious": {"valence": 0.30, "energy": 0.40, "acousticness": 0.35, "tempo": 95.0, "instrumentalness": 0.45},
    "dreamy": {"valence": 0.45, "energy": 0.35, "acousticness": 0.50, "tempo": 95.0, "instrumentalness": 0.40},
    "dark": {"valence": 0.15, "energy": 0.55, "acousticness": 0.20, "tempo": 110.0},
    # Energy level
    "energetic": {"energy": 0.90, "tempo": 140.0, "danceability": 0.70, "acousticness": 0.10},
    "upbeat": {"valence": 0.80, "energy": 0.80, "tempo": 125.0, "danceability": 0.75},
    "calm": {"energy": 0.25, "tempo": 80.0, "acousticness": 0.75, "valence": 0.50},
    "chill": {"energy": 0.40, "tempo": 90.0, "acousticness": 0.50, "valence": 0.55, "danceability": 0.60},
    "sleepy": {"energy": 0.12, "tempo": 70.0, "acousticness": 0.85, "instrumentalness": 0.60, "danceability": 0.30},
    "meditative": {"energy": 0.12, "tempo": 70.0, "acousticness": 0.70, "instrumentalness": 0.85, "valence": 0.40, "danceability": 0.25},
    "worship": {"energy": 0.45, "tempo": 95.0, "acousticness": 0.50, "valence": 0.60, "instrumentalness": 0.05},
    # Time, weather, and seasons
    "late night": {"energy": 0.40, "tempo": 95.0, "valence": 0.35, "acousticness": 0.35},
    "evening": {"energy": 0.45, "tempo": 100.0, "valence": 0.55, "acousticness": 0.50},
    "morning": {"energy": 0.50, "tempo": 105.0, "valence": 0.65, "acousticness": 0.50},
    "rainy": {"energy": 0.30, "tempo": 85.0, "valence": 0.30, "acousticness": 0.70},
    "sunny": {"energy": 0.70, "tempo": 115.0, "valence": 0.80, "danceability": 0.70},
    "cozy": {"energy": 0.30, "tempo": 85.0, "valence": 0.55, "acousticness": 0.75},
    "autumn": {"energy": 0.40, "tempo": 95.0, "valence": 0.45, "acousticness": 0.65},
    "spring": {"energy": 0.55, "tempo": 110.0, "valence": 0.75, "acousticness": 0.60},
    "holiday": {"energy": 0.50, "tempo": 110.0, "valence": 0.75, "acousticness": 0.55},
    # Places and activities
    "focused": {"energy": 0.35, "tempo": 95.0, "acousticness": 0.55, "instrumentalness": 0.80},
    "workout": {"energy": 0.92, "tempo": 140.0, "danceability": 0.70, "acousticness": 0.05, "valence": 0.60},
    "party": {"energy": 0.85, "tempo": 125.0, "danceability": 0.85, "valence": 0.75, "acousticness": 0.05},
    "rave": {"energy": 0.95, "tempo": 132.0, "danceability": 0.80, "acousticness": 0.02, "instrumentalness": 0.50, "valence": 0.45},
    "tavern": {"energy": 0.65, "tempo": 115.0, "valence": 0.70, "acousticness": 0.70, "danceability": 0.60},
    "road trip": {"energy": 0.70, "tempo": 120.0, "valence": 0.65, "danceability": 0.60},
    "travel": {"energy": 0.50, "tempo": 105.0, "valence": 0.55, "acousticness": 0.45},
    "walking": {"energy": 0.55, "tempo": 110.0, "valence": 0.65, "acousticness": 0.45},
    "nature": {"energy": 0.45, "tempo": 105.0, "valence": 0.60, "acousticness": 0.75},
    "city": {"energy": 0.65, "tempo": 115.0, "valence": 0.50, "danceability": 0.65, "acousticness": 0.15},
    "cleaning": {"energy": 0.75, "tempo": 120.0, "valence": 0.80, "danceability": 0.75},
    "cooking": {"energy": 0.55, "tempo": 110.0, "valence": 0.70, "danceability": 0.65, "acousticness": 0.45},
    "gaming": {"energy": 0.80, "tempo": 130.0, "acousticness": 0.05, "instrumentalness": 0.50},
}


# Some moods are about a style of music more than its tempo or energy. Audio
# features alone can't tell a Bach suite from a tango with the same numbers,
# so these terms also limit songs to fitting genres (names as in the dataset).
MOOD_GENRES = {
    "fairytale": ["classical", "opera", "show-tunes"],
    "rave": ["techno", "house", "edm", "trance", "minimal-techno"],
    "tavern": ["folk"],
    "meditative": ["ambient", "new-age", "sleep"],
    "worship": ["gospel"],
}


# Genres that suit each mood. Unlike MOOD_GENRES, these don't limit the songs;
# songs in them rank higher (see "genre fit" in recommender.py). Audio features
# alone can't tell a folk ballad from a sertanejo hit with the same tempo and
# energy, so without this the top matches come from every genre at random.
# Names as in the dataset; not every mood needs every fitting genre.
GENRE_AFFINITY = {
    "happy": ["pop", "indie-pop", "power-pop", "dance", "funk", "soul", "disco", "afrobeat", "ska"],
    "sad": ["sad", "singer-songwriter", "acoustic", "indie-pop", "emo", "folk", "piano", "soul", "alt-rock"],
    "melancholic": ["sad", "singer-songwriter", "indie-pop", "folk", "acoustic", "piano", "trip-hop", "alt-rock"],
    "heartbroken": ["sad", "singer-songwriter", "pop", "acoustic", "soul", "emo", "indie-pop", "piano"],
    "lonely": ["sad", "singer-songwriter", "acoustic", "indie-pop", "folk", "piano", "trip-hop"],
    "longing": ["singer-songwriter", "sad", "soul", "indie-pop", "acoustic", "folk", "piano"],
    "homesick": ["folk", "acoustic", "singer-songwriter", "country", "indie-pop"],
    "grieving": ["piano", "classical", "sad", "ambient", "singer-songwriter", "acoustic"],
    "numb": ["trip-hop", "ambient", "sad", "alt-rock", "emo", "indie-pop", "electronic"],
    "angry": ["metal", "hard-rock", "punk", "punk-rock", "metalcore", "hardcore", "heavy-metal", "industrial", "alt-rock"],
    "anxious": ["ambient", "new-age", "piano", "acoustic", "chill", "classical"],
    "romantic": ["soul", "singer-songwriter", "acoustic", "pop", "indie-pop", "jazz"],
    "sensual": ["soul", "funk", "hip-hop", "trip-hop", "pop", "deep-house"],
    "nostalgic": ["rock-n-roll", "power-pop", "indie-pop", "folk", "soul", "disco", "rock", "alt-rock", "singer-songwriter"],
    "reflective": ["singer-songwriter", "acoustic", "folk", "piano", "ambient", "indie-pop", "jazz", "trip-hop"],
    "hopeful": ["indie-pop", "pop", "folk", "acoustic", "singer-songwriter", "power-pop"],
    "grateful": ["acoustic", "folk", "gospel", "soul", "singer-songwriter", "indie-pop"],
    "excited": ["pop", "dance", "edm", "power-pop", "electro", "house", "indie-pop"],
    "triumphant": ["rock", "hard-rock", "hip-hop", "edm", "pop", "alt-rock", "power-pop"],
    "confident": ["hip-hop", "pop", "dance", "funk", "electro", "dancehall"],
    "playful": ["pop", "indie-pop", "power-pop", "funk", "ska", "disco"],
    "rebellious": ["punk", "punk-rock", "alt-rock", "hard-rock", "garage", "metal", "emo"],
    "epic": ["classical", "opera", "heavy-metal", "hard-rock", "trance", "rock", "show-tunes"],
    "fairytale": ["classical", "opera", "show-tunes", "piano", "new-age"],
    "mysterious": ["trip-hop", "ambient", "jazz", "electronic", "goth", "minimal-techno"],
    "dreamy": ["ambient", "indie-pop", "trip-hop", "chill", "new-age", "electronic", "psych-rock"],
    "dark": ["goth", "industrial", "black-metal", "death-metal", "trip-hop", "metal", "emo"],
    "energetic": ["edm", "dance", "electro", "house", "hip-hop", "hard-rock", "drum-and-bass", "dubstep"],
    "upbeat": ["pop", "dance", "indie-pop", "power-pop", "funk", "disco", "ska"],
    "calm": ["acoustic", "ambient", "piano", "classical", "new-age", "chill", "singer-songwriter"],
    "chill": ["chill", "trip-hop", "indie-pop", "jazz", "soul", "acoustic", "deep-house"],
    "sleepy": ["sleep", "ambient", "piano", "classical", "new-age", "acoustic"],
    "meditative": ["ambient", "new-age", "sleep", "classical", "piano"],
    "worship": ["gospel"],
    "late night": ["trip-hop", "chill", "jazz", "soul", "indie-pop", "deep-house", "electronic"],
    "evening": ["jazz", "soul", "chill", "acoustic", "indie-pop", "singer-songwriter"],
    "morning": ["acoustic", "indie-pop", "folk", "singer-songwriter", "jazz", "chill", "soul"],
    "rainy": ["acoustic", "singer-songwriter", "folk", "indie-pop", "jazz", "piano", "chill", "trip-hop"],
    "sunny": ["pop", "indie-pop", "dancehall", "afrobeat", "house", "power-pop", "ska"],
    "cozy": ["acoustic", "folk", "jazz", "singer-songwriter", "piano", "indie-pop", "chill"],
    "autumn": ["folk", "acoustic", "singer-songwriter", "indie-pop", "alt-rock", "jazz"],
    "spring": ["indie-pop", "acoustic", "folk", "pop", "singer-songwriter"],
    "holiday": ["pop", "soul", "jazz", "show-tunes", "gospel", "rock-n-roll"],
    "focused": ["ambient", "classical", "piano", "chill", "electronic", "minimal-techno", "new-age"],
    "workout": ["edm", "hip-hop", "hard-rock", "dance", "electro", "hardstyle", "drum-and-bass", "dubstep"],
    "party": ["dance", "edm", "house", "hip-hop", "pop", "party", "club", "dancehall", "electro"],
    "rave": ["techno", "house", "edm", "trance", "minimal-techno", "drum-and-bass", "hardstyle"],
    "tavern": ["folk"],
    "road trip": ["rock", "alt-rock", "indie-pop", "country", "pop", "rock-n-roll", "power-pop"],
    "travel": ["indie-pop", "folk", "acoustic", "chill", "pop"],
    "walking": ["indie-pop", "pop", "folk", "chill", "acoustic"],
    "nature": ["folk", "acoustic", "singer-songwriter", "ambient", "new-age", "country"],
    "city": ["hip-hop", "indie-pop", "electronic", "house", "jazz", "trip-hop"],
    "cleaning": ["pop", "dance", "disco", "funk", "indie-pop", "power-pop"],
    "cooking": ["jazz", "soul", "funk", "pop", "indie-pop", "acoustic"],
    "gaming": ["electronic", "edm", "electro", "drum-and-bass", "dubstep", "metal"],
}


def get_genre_affinity(
    mood_terms: list[str] | dict[str, float],
    extra_genres: list[str] | None = None,
) -> dict[str, float]:
    """How well each genre suits the mood, 0–1. Genres not listed fit 0.

    A genre listed by every mood term (weighted by how strongly it's meant)
    gets 1.0; one listed by half of them gets 0.5. extra_genres (e.g. the
    in-browser AI's guesses) count like one more mood term.

    {"rainy": 1, "morning": 1} -> {"acoustic": 1.0, "jazz": 1.0, "piano": 0.5, ...}
    """
    weights = mood_terms if isinstance(mood_terms, dict) else dict.fromkeys(mood_terms, 1.0)
    weights = {term: weight for term, weight in weights.items() if term in GENRE_AFFINITY}

    sources = [(GENRE_AFFINITY[term], weight) for term, weight in weights.items()]
    if extra_genres:
        sources.append((extra_genres, 1.0))

    total = sum(weight for _, weight in sources)
    if total == 0:
        return {}

    affinity = {}
    for genres, weight in sources:
        for genre in genres:
            affinity[genre] = affinity.get(genre, 0) + weight

    return {genre: round(value / total, 3) for genre, value in affinity.items()}


def get_preferred_genres(mood_terms: list[str]) -> list[str]:
    """Genres the mood terms point to, e.g. ["fairytale"] -> ["classical", "opera", "show-tunes"].

    Empty when none of the terms has preferred genres.
    """
    genres = []

    for term in mood_terms:
        for genre in MOOD_GENRES.get(term, []):
            if genre not in genres:
                genres.append(genre)

    return genres


def get_target_features(
    mood_terms: list[str] | dict[str, float],
) -> dict[str, float]:
    """Combine mood terms into one target value per audio feature.

    Each feature is the average of the values from the terms that mention it,
    so ["energetic", "sad"] meets in the middle on energy. Features that no
    term mentions, and terms that aren't in MOOD_TARGETS, fall back to neutral.

    mood_terms can also be {term: weight}, e.g. from extract_weighted_mood_terms():
    {"sad": 0.5, "excited": 1.5} leans three times more toward excited.
    """
    weights = mood_terms if isinstance(mood_terms, dict) else dict.fromkeys(mood_terms, 1.0)
    targets = {}

    for feature in RECOMMENDATION_FEATURES:
        weighted = [
            (MOOD_TARGETS[term][feature], weight)
            for term, weight in weights.items()
            if feature in MOOD_TARGETS.get(term, {})
        ]

        if weighted:
            total_weight = sum(weight for _, weight in weighted)
            targets[feature] = round(sum(value * weight for value, weight in weighted) / total_weight, 3)
        else:
            targets[feature] = NEUTRAL_TARGETS[feature]

    return targets


def create_target_vector(mood_terms: list[str] | dict[str, float]) -> np.ndarray:
    """Target features as a vector in the same order as create_song_vector()."""
    targets = get_target_features(mood_terms)

    return np.array(
        [targets[feature] for feature in RECOMMENDATION_FEATURES],
        dtype=float,
    )
