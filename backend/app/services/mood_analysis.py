import re

# Each mood term and the words or phrases that signal it.
# Write everything in lowercase with spaces instead of hyphens ("late night", not "late-night"),
# because the description is normalized the same way before matching.
MOOD_TERMS = {
    # Feelings
    "happy": ["happy", "happiness", "joyful", "joy", "cheerful", "good mood", "great mood", "feel good", "feeling good", "feeling great", "glad", "delighted", "elated", "on top of the world", "good day", "best day", "smiling", "giggly", "happier", "happiest", "feliz", "alegre", "alegria", "alegría"],
    "sad": ["sad", "sadness", "unhappy", "depressed", "depressing", "depression", "gloomy", "crying", "cry", "cried", "tearful", "tears", "miserable", "feeling down", "feeling blue", "upset", "hurt", "hurting", "in my feels", "in my feelings", "sad girl", "sad boy", "sad boi", "emo", "rough day", "bad day", "sadder", "saddest", "triste", "tristes", "llorar", "melancolia", "melancolía"],
    "melancholic": ["melancholic", "melancholy", "bittersweet", "wistful", "somber", "sombre", "moody", "pensive", "brooding"],
    "heartbroken": ["heartbroken", "heartbreak", "heartache", "breakup", "break up", "broke up", "broken heart", "missing my ex", "my ex", "dumped", "got dumped", "cheated on", "situationship", "ghosted", "unrequited"],
    "lonely": ["lonely", "loneliness", "alone", "isolated", "by myself", "on my own", "left out", "nobody", "no friends", "solitude"],
    "longing": ["longing", "yearning", "pining", "missing someone", "missing you", "miss you", "miss him", "miss her", "miss them", "long distance", "far apart", "waiting for you", "missing everyone", "miss everyone", "already missing"],
    "homesick": ["homesick", "missing home", "miss home", "far from home", "missing my family", "miss my family", "moved away", "first semester"],
    "grieving": ["grieving", "grief", "mourning", "funeral", "passed away", "lost someone", "rest in peace", "memorial", "lost my mom", "lost my dad", "lost my grandma", "lost my grandpa", "lost my dog", "lost my cat", "lost my best friend"],
    "numb": ["numb", "empty", "hollow", "emotionless", "dissociating", "dissociated", "zoned out", "ghost", "going through the motions", "burnt out", "burned out", "burnout", "drained"],
    "angry": ["angry", "anger", "mad", "furious", "rage", "raging", "pissed", "pissed off", "frustrated", "aggressive", "livid", "fuming", "bitter", "jealous", "petty", "revenge", "spiteful", "fed up", "irritated", "annoyed"],
    "anxious": ["anxious", "anxiety", "nervous", "stressed", "stress", "stressful", "overwhelmed", "worried", "tense", "panic", "panicking", "on edge", "restless", "overthinking", "jittery", "dread", "scared", "afraid"],
    "romantic": ["romantic", "romance", "love", "in love", "lovestruck", "date night", "first date", "crush", "valentine", "valentines", "anniversary", "intimate", "falling for", "butterflies", "wedding", "first dance", "honeymoon", "cuddling", "cuddle", "soulmate", "my person", "on a date", "amor", "enamorado", "enamorada", "romantica", "romántica"],
    "sensual": ["sexy", "sultry", "seductive", "steamy", "sensual", "flirty", "flirting", "bedroom", "slow jam", "slow jams"],
    "nostalgic": ["nostalgic", "nostalgia", "throwback", "throwbacks", "reminiscing", "memories", "memory lane", "old times", "good old days", "childhood", "back in the day", "high school", "growing up", "old photos", "2000s", "90s", "80s", "y2k", "retro", "vintage"],
    "reflective": ["reflective", "reflecting", "thoughtful", "introspective", "contemplative", "pondering", "thinking about life", "deep thoughts", "soul searching", "existential", "existential crisis", "life choices", "philosophical", "journaling", "staring at the ceiling"],
    "hopeful": ["hopeful", "hope", "optimistic", "inspired", "inspiring", "uplifting", "new beginning", "new beginnings", "fresh start", "new chapter", "moving on", "healing", "freedom", "liberated", "free spirit", "free spirited", "better days", "manifesting"],
    "grateful": ["grateful", "gratitude", "thankful", "blessed", "appreciative", "contentment", "fulfilled", "at peace", "wholesome"],
    "excited": ["excited", "exciting", "cant wait", "thrilled", "stoked", "giddy", "buzzing", "anticipation", "countdown", "big news"],
    "triumphant": ["triumphant", "victorious", "victory", "won", "winning", "we won", "proud", "accomplished", "achievement", "nailed it", "graduation", "graduating", "graduated", "promotion", "got the job", "champion", "celebratory"],
    "confident": ["confident", "confidence", "empowered", "powerful", "unstoppable", "bold", "boss", "boss mode", "main character", "main character energy", "that girl", "slay", "slaying", "unbothered", "glow up", "glowing up", "getting ready", "get ready with me", "strutting", "swagger", "self love", "baddie"],
    "playful": ["playful", "silly", "goofy", "quirky", "whimsical", "cheeky", "carefree", "lighthearted", "light hearted", "fun loving", "chaotic good", "giggling"],
    "rebellious": ["rebellious", "rebel", "defiant", "chaotic", "unhinged", "feral", "villain", "villain era", "reckless", "wild", "no rules", "breaking rules", "angsty", "teen angst", "punk"],
    "epic": ["epic", "heroic", "hero", "cinematic", "adventure", "adventurous", "quest", "battle", "conquer", "legendary", "movie scene", "training montage", "boss fight", "final boss"],
    "fairytale": ["fairytale", "fairytales", "fairy tale", "fairy tales", "knight", "knights", "knighted", "princess", "princesses", "prince", "princes", "royal", "royals", "royalty", "castle", "castles", "kingdom", "enchanted", "once upon a time", "happily ever after", "ballroom", "royal ball", "disney"],
    "mysterious": ["mysterious", "mystery", "secretive", "noir", "detective", "suspense", "suspenseful", "spy", "heist", "intrigue"],
    "dreamy": ["dreamy", "dreaming", "daydreaming", "daydream", "ethereal", "floating", "spacey", "hazy", "stargazing", "stars", "starry", "moonlight", "moon", "outer space", "cosmic", "galaxy", "clouds", "delulu", "romanticizing", "romanticize", "romanticizing my life", "magical", "whimsy"],
    "dark": ["dark", "eerie", "haunting", "haunted", "ominous", "sinister", "spooky", "creepy", "horror", "halloween", "gothic", "goth", "witchy", "villainous", "darker", "darkest"],
    # Energy level
    "energetic": ["energetic", "energy", "energized", "hyped", "hype", "hyped up", "pumped", "pumped up", "intense", "adrenaline", "fired up", "high energy", "amped", "turnt", "turn up", "lets go", "beast mode", "go mode", "faster", "louder", "more energetic", "more energy", "harder"],
    "upbeat": ["upbeat", "up beat", "lively", "bouncy", "peppy", "fun", "feel good music", "bright", "sunny disposition", "good vibes", "positive", "positive vibes", "bubbly", "more upbeat", "brighter"],
    "calm": ["calm", "calming", "peaceful", "peace", "relaxed", "relaxing", "relax", "serene", "soothing", "tranquil", "gentle", "quiet", "unwind", "unwinding", "wind down", "winding down", "decompress", "decompressing", "bath", "bubble bath", "self care", "spa", "slow morning", "slow mornings", "calmer", "calmest", "softer", "slower", "tranquila", "tranquilo", "relajante"],
    "chill": ["chill", "chilling", "chilled", "chillin", "laid back", "mellow", "easygoing", "easy going", "lofi", "lo fi", "vibing", "lazy", "lazy day", "lazy sunday", "lounging", "doing nothing", "bed rot", "bed rotting", "hanging out", "hangout", "kicking back", "chiller", "more chill", "more relaxed"],
    "sleepy": ["sleepy", "sleep", "sleeping", "tired", "exhausted", "bedtime", "drowsy", "nap", "napping", "falling asleep", "fall asleep", "lullaby", "insomnia help", "power nap", "yawning", "low energy", "no energy left", "wiped out"],
    "meditative": ["meditative", "meditation", "meditating", "mindful", "mindfulness", "zen", "yoga", "breathing", "breathwork", "grounding", "spiritual", "healing energy", "sound bath"],
    "worship": ["worship", "church", "praise", "gospel", "prayer", "praying", "pray", "sunday service", "faith"],
    # Time, weather, and seasons
    "late night": ["late night", "late at night", "at night", "night", "nights", "tonight", "midnight", "after midnight", "nighttime", "night drive", "night driving", "all nighter", "2am", "3am", "4am", "2 am", "3 am", "4 am", "cant sleep", "insomnia", "after hours", "city lights", "neon"],
    "evening": ["evening", "golden hour", "dusk", "twilight", "after work", "after school", "dinner"],
    "morning": ["morning", "mornings", "sunrise", "waking up", "wake up", "early morning", "breakfast", "dawn", "first coffee", "morning routine", "morning coffee"],
    "rainy": ["rainy", "rain", "raining", "drizzle", "drizzly", "storm", "stormy", "thunderstorm", "thunder", "overcast", "cloudy", "grey day", "gray day", "foggy", "fog", "misty"],
    "sunny": ["sunny", "sunshine", "summer", "summertime", "beach", "sunset", "warm day", "poolside", "pool party", "ocean", "waves", "tropical", "island", "vacation", "heatwave", "sunbathing", "boat"],
    "cozy": ["cozy", "cosy", "fireplace", "blanket", "snowy", "snow", "snowing", "winter", "candlelight", "candles", "hot chocolate", "coffee shop", "cafe", "tea", "sweater weather", "hygge", "cabin", "cuddled up", "pajamas"],
    "autumn": ["autumn", "fall vibes", "fall season", "fall day", "fall afternoon", "leaves changing", "falling leaves", "pumpkin", "pumpkin spice", "october", "harvest"],
    "spring": ["spring", "springtime", "blooming", "flowers", "cherry blossom", "cherry blossoms", "picnic", "garden", "gardening", "april"],
    "holiday": ["christmas", "xmas", "holiday", "holidays", "holiday season", "festive", "thanksgiving", "new year", "new years", "new years eve", "hanukkah", "santa", "decorating the tree", "family dinner"],
    # Places and activities
    "focused": ["focused", "focus", "focusing", "study", "studying", "homework", "working", "work", "reading", "coding", "programming", "concentrate", "concentrating", "concentration", "deep work", "exam", "exams", "finals", "midterms", "essay", "writing", "productive", "productivity", "office", "wfh", "work from home", "library", "lock in", "locked in", "locking in"],
    "workout": ["workout", "working out", "gym", "running", "run", "jogging", "lifting", "weightlifting", "exercise", "exercising", "training", "cardio", "spin class", "hiit", "crossfit", "game day", "big game", "warm up", "pre workout", "marathon", "boxing", "sprint", "work out"],
    "party": ["party", "partying", "dance", "dancing", "club", "clubbing", "pregame", "pregaming", "celebrating", "celebration", "night out", "girls night", "birthday", "bday", "lit", "dance floor", "bachelorette", "house party", "frat party", "karaoke", "fiesta", "bailar", "perreo"],
    "rave": ["rave", "raving", "warehouse", "techno", "edm", "festival", "music festival", "edc", "coachella", "bass drop", "strobe", "glow sticks"],
    "tavern": ["tavern", "medieval", "renaissance", "ren faire", "renaissance faire", "pub", "mead", "pirate", "pirates", "sea shanty", "sea shanties", "viking", "vikings", "irish pub", "bard"],
    "road trip": ["road trip", "driving", "drive", "highway", "long drive", "cruising", "commute", "commuting", "windows down", "open road", "car ride", "car"],
    "travel": ["travel", "traveling", "travelling", "airport", "flight", "plane", "on the plane", "train ride", "on the train", "bus ride", "backpacking", "abroad", "exploring a new city", "new city", "wanderlust"],
    "walking": ["walking", "walk", "walks", "stroll", "strolling", "wandering", "exploring", "city walk", "hot girl walk", "coffee run"],
    "nature": ["nature", "forest", "woods", "hiking", "hike", "mountains", "mountain", "camping", "campfire", "outdoors", "lake", "river", "trail", "national park", "countryside", "farm", "meadow"],
    "city": ["city", "downtown", "urban", "skyline", "rooftop", "subway", "streets", "big city", "new york", "nyc", "tokyo", "london", "paris", "san francisco", "los angeles"],
    "cleaning": ["cleaning", "chores", "tidying", "tidy", "laundry", "organizing", "doing dishes", "dishes", "deep clean", "reset day", "sunday reset"],
    "cooking": ["cooking", "baking", "kitchen", "making dinner", "cooking dinner", "meal prep", "brunch"],
    "gaming": ["gaming", "video games", "video game", "playing games", "gamer", "speedrun", "ranked", "minecraft", "fortnite"],
}

# Words that flip the meaning of the term that follows ("not sad", "no energy")
NEGATIONS = {"not", "no", "never", "without", "isnt", "dont", "arent", "wasnt", "doesnt", "cant", "wont", "nothing"}

# Words allowed between a negation and the term ("not feeling very happy")
FILLERS = {"very", "really", "so", "too", "that", "feeling", "feel", "particularly", "exactly", "in", "a", "an", "the", "any", "much"}

# How much a term counts when one of these comes right before it.
# "a little sad and very excited" leans more excited than sad.
SOFTENERS = {"slightly", "a little", "a little bit", "a bit", "kinda", "kind of", "sort of", "somewhat", "mildly", "lowkey", "low key", "semi", "barely"}
INTENSIFIERS = {"very", "really", "so", "super", "extremely", "incredibly", "deeply", "totally", "completely", "highkey", "high key", "insanely", "crazy", "hella", "absolutely", "overwhelmingly", "seriously"}
SOFTENED_WEIGHT = 0.5
INTENSIFIED_WEIGHT = 1.5

# Words that can sit between an intensity word and the term ("so very tired",
# "a little bit sad", "kind of feeling nostalgic")
INTENSITY_FILLERS = {"feeling", "feel", "im", "i", "am", "and", "but", "also", "just", "getting", "a"}

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


def get_intensity(text_before_match: str) -> float:
    """How much a term counts, from the words right before it: 0.5, 1.0, or 1.5."""
    words = text_before_match.split()

    # Look at the last few words, skipping filler like "feeling"
    for _ in range(3):
        for size in (3, 2, 1):  # "a little bit" before "a little" before "a"
            phrase = " ".join(words[-size:]) if len(words) >= size else None

            if phrase in SOFTENERS:
                return SOFTENED_WEIGHT

            if phrase in INTENSIFIERS:
                return INTENSIFIED_WEIGHT

        if words and words[-1] in INTENSITY_FILLERS:
            words.pop()
        else:
            break

    return 1.0


def extract_weighted_mood_terms(description: str) -> dict[str, float]:
    """The mood terms found in a description and how strongly each is meant, in order.

    "a little sad but very excited" -> {"sad": 0.5, "excited": 1.5}
    A term mentioned twice keeps its strongest weight.
    """
    text = normalize_description(description)
    weights = {}

    for match in PHRASE_PATTERN.finditer(text):
        term = PHRASE_TO_TERM[match.group()]
        before = text[:match.start()]

        if is_negated(before):
            continue

        weights[term] = max(weights.get(term, 0), get_intensity(before))

    return weights


def extract_mood_terms(description: str) -> list[str]:
    """Return the mood terms found in a description, in the order they appear.

    "Nostalgic late-night drive in the rain" -> ["nostalgic", "late night", "road trip", "rainy"]
    """
    return list(extract_weighted_mood_terms(description))
