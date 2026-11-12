import re

# Each mood term and the words or phrases that signal it.
# Write everything in lowercase with spaces instead of hyphens ("late night", not "late-night"),
# because the description is normalized the same way before matching.
MOOD_TERMS = {
    # Feelings
    "happy": ["happy", "happiness", "joyful", "joy", "cheerful", "good mood", "great mood", "feel good", "feeling good", "feeling great"],
    "sad": ["sad", "sadness", "unhappy", "depressed", "depressing", "gloomy", "crying", "cry", "tearful", "miserable"],
    "melancholic": ["melancholic", "melancholy", "bittersweet", "wistful", "somber", "moody"],
    "heartbroken": ["heartbroken", "heartbreak", "heartache", "breakup", "break up", "broke up", "broken heart", "missing my ex", "dumped"],
    "lonely": ["lonely", "loneliness", "alone", "isolated", "by myself", "on my own"],
    "angry": ["angry", "anger", "mad", "furious", "rage", "pissed", "frustrated", "aggressive"],
    "anxious": ["anxious", "anxiety", "nervous", "stressed", "stress", "stressful", "overwhelmed", "worried", "tense"],
    "romantic": ["romantic", "romance", "love", "in love", "date night", "crush", "valentine", "anniversary", "intimate", "falling for"],
    "nostalgic": ["nostalgic", "nostalgia", "throwback", "reminiscing", "memories", "old times", "good old days", "childhood", "back in the day", "high school"],
    "hopeful": ["hopeful", "hope", "optimistic", "inspired", "inspiring", "uplifting", "new beginning", "fresh start"],
    "confident": ["confident", "confidence", "empowered", "powerful", "unstoppable", "bold", "boss"],
    "dreamy": ["dreamy", "dreaming", "daydreaming", "ethereal", "floating", "spacey", "hazy"],
    "dark": ["dark", "eerie", "haunting", "ominous", "sinister", "spooky"],
    # Energy level
    "energetic": ["energetic", "energy", "energized", "hyped", "hype", "pumped", "pumped up", "intense", "adrenaline", "fired up", "high energy"],
    "upbeat": ["upbeat", "up beat", "lively", "bouncy", "peppy", "fun", "feel good music", "bright"],
    "calm": ["calm", "calming", "peaceful", "relaxed", "relaxing", "relax", "serene", "soothing", "tranquil", "gentle", "quiet", "unwind", "unwinding", "wind down"],
    "chill": ["chill", "chilling", "chilled", "laid back", "mellow", "easygoing", "easy going", "lofi", "lo fi", "vibing"],
    "sleepy": ["sleepy", "sleep", "sleeping", "tired", "exhausted", "bedtime", "drowsy", "nap", "falling asleep"],
    # Time and weather
    "late night": ["late night", "late at night", "midnight", "after midnight", "nighttime", "night drive", "night driving", "all nighter", "2am", "3am", "2 am", "3 am", "cant sleep", "insomnia"],
    "morning": ["morning", "sunrise", "waking up", "wake up", "early", "breakfast", "dawn"],
    "rainy": ["rainy", "rain", "raining", "drizzle", "drizzly", "storm", "stormy", "thunderstorm", "overcast", "cloudy", "grey day", "gray day"],
    "sunny": ["sunny", "sunshine", "summer", "beach", "sunset", "warm day", "poolside"],
    "cozy": ["cozy", "cosy", "fireplace", "blanket", "snowy", "winter", "candlelight", "hot chocolate", "coffee shop"],
    # Activities
    "focused": ["focused", "focus", "focusing", "study", "studying", "homework", "working", "reading", "coding", "concentrate", "concentrating", "concentration", "deep work"],
    "workout": ["workout", "working out", "gym", "running", "run", "jogging", "lifting", "exercise", "exercising", "training", "cardio"],
    "party": ["party", "partying", "dance", "dancing", "club", "clubbing", "pregame", "celebrating", "celebration", "night out"],
    "road trip": ["road trip", "driving", "drive", "highway", "long drive", "cruising", "commute"],
}

# Words that flip the meaning of the term that follows ("not sad", "no energy")
NEGATIONS = {"not", "no", "never", "without", "isnt", "dont", "arent", "wasnt", "doesnt", "cant", "wont", "nothing"}

# Words allowed between a negation and the term ("not feeling very happy")
FILLERS = {"very", "really", "so", "too", "that", "feeling", "feel", "particularly", "exactly", "in", "a", "an", "the", "any", "much"}

# phrase -> mood term, e.g. "studying" -> "focused"
PHRASE_TO_TERM = {
    phrase: term
    for term, phrases in MOOD_TERMS.items()
    for phrase in phrases
}

# One pattern that finds any phrase as a whole word. Longer phrases come first
# so "late night" is matched before a shorter phrase could claim part of it.
PHRASE_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(phrase) for phrase in sorted(PHRASE_TO_TERM, key=len, reverse=True))
    + r")\b"
)


def normalize_description(description: str) -> str:
    text = description.lower()
    text = re.sub(r"['’`]", "", text)        # "can't" -> "cant"
    text = re.sub(r"[^a-z0-9]+", " ", text)  # punctuation and hyphens become spaces
    return text.strip()


def is_negated(text_before_match: str) -> bool:
    words_before = text_before_match.split()

    while words_before and words_before[-1] in FILLERS:
        words_before.pop()

    return bool(words_before) and words_before[-1] in NEGATIONS


def extract_mood_terms(description: str) -> list[str]:
    """Return the mood terms found in a description, in the order they appear.

    "Nostalgic late-night drive in the rain" -> ["nostalgic", "late night", "rainy"]
    """
    text = normalize_description(description)
    terms = []

    for match in PHRASE_PATTERN.finditer(text):
        term = PHRASE_TO_TERM[match.group()]

        if term in terms:
            continue

        if is_negated(text[:match.start()]):
            continue

        terms.append(term)

    return terms
