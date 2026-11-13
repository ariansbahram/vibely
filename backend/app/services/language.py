"""Work out which language songs are in, and which languages a user wants.

The song dataset has no language field, so it's estimated from the title,
the artist's other titles, and the genre:

1. The script: Hangul is Korean, kana Japanese, Cyrillic Russian, etc.
2. For Latin script, common words vote: "corazón" and "quiero" for Spanish,
   "und" and "nicht" for German, "the" and "love" for English. Letters like
   ñ, ã, ş, å vote too.
3. Otherwise a genre that's mostly one language decides ("k-pop" is Korean,
   even for English-looking titles), then a clearly English title, then the
   artist's language (the vote over all their titles), else English.

It's a heuristic: mostly right, sometimes wrong for a single song.
"""

import re
from collections import Counter
from functools import lru_cache

import numpy as np

from app.services.dataset import DATASET_PATH, load_dataset

# The languages take ~30 s to work out for 1.16M songs, so they're saved next to
# the dataset and only worked out again if the dataset or these rules change
LANGUAGE_CACHE_PATH = DATASET_PATH.with_name("song_languages.npz")
LANGUAGE_RULES_VERSION = 4

ENGLISH = "en"

LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "pt": "Portuguese", "fr": "French", "de": "German", "it": "Italian",
    "nl": "Dutch", "sv": "Swedish", "tr": "Turkish", "id": "Indonesian", "tl": "Tagalog", "vi": "Vietnamese",
    "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "ru": "Russian", "ar": "Arabic", "hi": "Hindi",
    "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "pa": "Punjabi", "th": "Thai", "el": "Greek", "he": "Hebrew",
}

# Scripts that give the language away. Japanese is checked before Chinese,
# since Japanese titles mix kana with Chinese characters.
SCRIPTS = [
    ("ko", re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]")),
    ("ja", re.compile(r"[぀-ヿ]")),
    ("zh", re.compile(r"[一-鿿]")),
    ("ru", re.compile(r"[Ѐ-ӿ]")),
    ("ar", re.compile(r"[؀-ۿ]")),
    ("hi", re.compile(r"[ऀ-ॿ]")),
    ("bn", re.compile(r"[ঀ-৿]")),
    ("pa", re.compile(r"[਀-੿]")),
    ("ta", re.compile(r"[஀-௿]")),
    ("te", re.compile(r"[ఀ-౿]")),
    ("th", re.compile(r"[฀-๿]")),
    ("el", re.compile(r"[Ͱ-Ͽ]")),
    ("he", re.compile(r"[֐-׿]")),
]

# Words that point to a language. Only words that are rare in English titles,
# so "me", "no", "de" (as in "Lana Del Rey"?) aren't used for Spanish.
LANGUAGE_WORDS = {
    "es": "el la los las que y mi tu te una por para amor corazon quiero eres como mas yo todo nada "
          "noche vida bailar cancion ella contigo ti se mundo cielo nunca siempre tiempo corazón canción "
          "también besos amigo dime donde cuando porque tus mis estoy esta dios hasta canciones triste tristes "
          "llorar feliz fiesta musica música alegre tranquila tranquilo relajante enamorado enamorada",
    "pt": "nao não eu voce você meu minha coração coracao pra saudade uma da dos das ao seu sua tá vou quero "
          "tudo nós sem ela ele mais meu vai fazer ser tem já ninguém",
    "fr": "le les des et je une est pas mon moi toi sur dans pour avec cest jai qui ce au ça mes tes nous vous "
          "rien tout coeur amour",
    "de": "der das und ich nicht ist mit mein dich mich ein eine auf für fur liebe wir sie zu kein nur noch "
          "auch wie bin hab mir dir wenn",
    "it": "il di che non io sei mio mia per sono della cuore amore tutto questa questo ancora perché perche "
          "sempre vita",
    "tr": "bir ve sen bu aşk için gibi değil yok seni beni olmaz sevgilim",
    "id": "yang aku kau kamu cinta tak ini itu untuk dari hati bisa jangan akan dengan sayang tanpa",
    "sv": "och jag det är inte på mig som att för till efter vi hon",
    "nl": "het een ik niet mijn jij zijn wat",
    "tl": "ang ng sa mga ko ikaw ako pag ibig mahal kita",
}

ENGLISH_WORDS = set("""
the you i me my your love it is to of and in on we be all dont im baby girl boy heart night feel cant know like
time way never up down get go what this that with for just so one back life light home day world want need wanna
gonna aint youre its ill ive were theyre wont about from out over into through every something nothing everything
somebody nobody tonight forever again away good bad better best dance dream dreams fire high low lost run fall
stay still yeah oh hey song songs only own say said tell talk think take make made come came give gave let little
""".split())

# Letters that point to a language, and how many votes they're worth.
# Letters only one language uses outweigh accents several languages share.
LETTER_HINTS = [
    ("vi", re.compile(r"[ăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]"), 4),
    ("es", re.compile(r"[ñ¿¡]"), 2),
    ("pt", re.compile(r"[ãõ]"), 2),
    ("tr", re.compile(r"[şğı]"), 2),
    ("sv", re.compile(r"[å]"), 2),
    ("de", re.compile(r"[ß]"), 2),
    ("es", re.compile(r"[áíóú]"), 1),   # also Portuguese, but rare in English titles either way
]

# Genres that are mostly in one language
GENRE_LANGUAGES = {
    "spanish": "es", "salsa": "es", "tango": "es", "sertanejo": "pt", "forro": "pt", "samba": "pt",
    "french": "fr", "german": "de", "swedish": "sv", "cantopop": "zh", "k-pop": "ko",
    "indian": "hi", "pop-film": "hi",
}

# How users ask for a language: "spanish songs", "k-pop", "bollywood", "in french"
LANGUAGE_REQUESTS = {
    "spanish": ["es"], "espanol": ["es"], "español": ["es"], "en espanol": ["es"], "latin": ["es", "pt"],
    "latino": ["es"], "reggaeton": ["es"], "portuguese": ["pt"], "brazilian": ["pt"], "french": ["fr"],
    "german": ["de"], "italian": ["it"], "dutch": ["nl"], "swedish": ["sv"], "turkish": ["tr"],
    "indonesian": ["id"], "tagalog": ["tl"], "filipino": ["tl"], "opm": ["tl"], "vietnamese": ["vi"],
    "korean": ["ko"], "k pop": ["ko"], "kpop": ["ko"], "japanese": ["ja"], "j pop": ["ja"], "jpop": ["ja"],
    "anime": ["ja"], "city pop": ["ja"], "chinese": ["zh"], "mandarin": ["zh"], "cantonese": ["zh"], "c pop": ["zh"],
    "cantopop": ["zh"], "mandopop": ["zh"], "hindi": ["hi"], "bollywood": ["hi"], "tamil": ["ta"],
    "kollywood": ["ta"], "telugu": ["te"], "punjabi": ["pa"], "bengali": ["bn"], "russian": ["ru"],
    "arabic": ["ar"], "thai": ["th"], "greek": ["el"], "hebrew": ["he"], "israeli": ["he"],
}

# "any language", "international": no limit
ANY_LANGUAGE = ["any language", "all languages", "every language", "different languages", "multilingual",
                "international", "world music", "global", "from around the world", "any genre and language"]

WORD = re.compile(r"[a-zà-ÿăđơưạ-ỹşğıñ]+")
VOTE_WORDS = {word: language for language, words in LANGUAGE_WORDS.items() for word in words.split()}


def get_word_votes(text: str) -> Counter:
    """How many words and letters in the text point to each language."""
    text = text.lower()
    votes = Counter()

    for language, pattern in SCRIPTS:
        if pattern.search(text):
            votes[language] += 10   # the script settles it
            return votes

    for language, pattern, weight in LETTER_HINTS:
        if pattern.search(text):
            votes[language] += weight

    for word in WORD.findall(text.replace("'", "").replace("’", "")):
        if word in ENGLISH_WORDS:
            votes[ENGLISH] += 1
        elif word in VOTE_WORDS:
            votes[VOTE_WORDS[word]] += 1

    return votes


def get_text_language(text: str, min_votes: int = 1) -> str | None:
    """The language a short text is most likely in, or None if there's no clear sign."""
    votes = get_word_votes(text)

    if not votes:
        return None

    (best, count), *rest = votes.most_common(2) + [(None, 0)]
    if count < min_votes or (rest and rest[0][1] == count):
        return None   # no votes, or a tie

    # Short English words ("me", "to", "i") turn up in titles in many languages,
    # so one English word alone isn't enough
    if best == ENGLISH and count < 2:
        return None

    return best


@lru_cache(maxsize=1)
def get_artist_languages() -> dict[str, str]:
    """{artist name: language} from the votes of all their titles (only clear cases)."""
    dataset = load_dataset()
    totals: dict[str, Counter] = {}

    for artist, title in zip(dataset["artist_name"].astype(str), dataset["track_name"].astype(str)):
        totals.setdefault(artist, Counter()).update(get_word_votes(title))

    languages = {}
    for artist, votes in totals.items():
        if not votes:
            continue
        (best, count), *rest = votes.most_common(2) + [(None, 0)]
        # A clear majority: at least 2 votes and more than any other language
        if count >= 2 and count > (rest[0][1] if rest else 0):
            languages[artist] = best

    return languages


@lru_cache(maxsize=1)
def get_song_languages() -> tuple[np.ndarray, list[str]]:
    """Every song's language as a number, and the language codes the numbers stand for."""
    dataset = load_dataset()
    codes = list(LANGUAGE_NAMES)

    try:
        saved = np.load(LANGUAGE_CACHE_PATH)
        if (
            int(saved["version"]) == LANGUAGE_RULES_VERSION
            and len(saved["languages"]) == len(dataset)
            and list(saved["codes"]) == codes
        ):
            return saved["languages"], codes
    except (OSError, KeyError, ValueError):
        pass   # not saved yet, or saved by older rules

    languages = work_out_song_languages(dataset, codes)

    try:
        np.savez(LANGUAGE_CACHE_PATH, languages=languages, codes=np.array(codes), version=LANGUAGE_RULES_VERSION)
    except OSError:
        pass   # can't save (read-only folder): it's worked out again next time

    return languages, codes


def work_out_song_languages(dataset, codes: list[str]) -> np.ndarray:
    artist_languages = get_artist_languages()
    index = {code: number for number, code in enumerate(codes)}
    result = np.empty(len(dataset), dtype=np.int8)

    rows = zip(dataset["track_name"].astype(str), dataset["artist_name"].astype(str), dataset["genre"].astype(str))

    for row, (title, artist, genre) in enumerate(rows):
        votes = get_word_votes(title)
        foreign = [(language, count) for language, count in votes.items() if language != ENGLISH]
        english = votes.get(ENGLISH, 0)

        if foreign and max(count for _, count in foreign) > english:
            language = max(foreign, key=lambda pair: pair[1])[0]          # the title says so
        elif genre in GENRE_LANGUAGES:
            language = GENRE_LANGUAGES[genre]                              # k-pop, sertanejo, ...
        elif english >= 2 and not foreign:
            language = ENGLISH                                             # clearly English title
        else:
            language = artist_languages.get(artist, ENGLISH)

        result[row] = index.get(language, index[ENGLISH])

    return result


def get_language_mask(languages: set[str]) -> np.ndarray:
    """True for every song in one of these languages."""
    song_languages, codes = get_song_languages()
    wanted = [number for number, code in enumerate(codes) if code in languages]
    return np.isin(song_languages, wanted)


def get_requested_languages(text: str) -> tuple[list[str] | None, list[str]]:
    """Languages the user asked for, and how they said it.

    Returns (None, []) if they asked for any language ("international").
    Returns ([], []) if they didn't mention a language.
    """
    normalized = f" {re.sub(r'[^a-z0-9ñçáéíóúü]+', ' ', text.lower()).strip()} "

    if any(f" {phrase} " in normalized for phrase in ANY_LANGUAGE):
        return None, []

    languages, labels = [], []
    for phrase in sorted(LANGUAGE_REQUESTS, key=len, reverse=True):
        if f" {phrase} " in normalized:
            labels.append(phrase)
            normalized = normalized.replace(f" {phrase} ", " | ")
            for language in LANGUAGE_REQUESTS[phrase]:
                if language not in languages:
                    languages.append(language)

    return languages, labels


def get_artist_language(artist: str) -> str:
    """The language most of an artist's songs are in (English if the dataset doesn't have them)."""
    dataset = load_dataset()
    rows = np.flatnonzero(dataset["artist_name"].to_numpy() == artist)

    if rows.size == 0:
        return ENGLISH

    song_languages, codes = get_song_languages()
    return codes[np.bincount(song_languages[rows]).argmax()]
