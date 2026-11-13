"""Find the specific things a description names, besides moods: artists,
genres, and decades/years.

  "sad taylor swift songs"          -> artists ["Taylor Swift"]
  "songs like the weeknd"           -> artists ["The Weeknd"], cue "like"
  "chill jazz for studying"         -> genres ["jazz"]
  "early 2010s throwbacks"          -> years (2010, 2014)

Artist names are matched against the song dataset, so only artists it has can
be found. Names that are ordinary words ("King", "Future", "Ghost") only count
with a cue: "songs by Future", "Ghost songs", "music like King".
"""

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

from app.services.dataset import load_dataset
from app.services.mood_analysis import MOOD_TERMS, PHRASE_PATTERN

# An artist needs at least this Spotify popularity (on their best song) to be
# recognized without a cue. Keeps obscure artists named "Sunday" or "Coffee"
# from turning up whenever someone uses that word.
MIN_ARTIST_POPULARITY = 45
MIN_ONE_WORD_ARTIST_POPULARITY = 60

# The longest artist name, in words, that is looked for
MAX_ARTIST_WORDS = 6

# Ordinary English words. Artist names made only of these need a cue.
# Every word in the mood lists (rain, night, summer, love...) counts too.
COMMON_WORDS = set("""
a about above after again against all almost alone along already also always am among an and another any anything
are around as at away back bad be beautiful because been before being below best better between big black blue body
boy boys but by call came can car change child city cold come coming could cry dance day days dead dear did do does
done down dream dreams drive drop each earth easy end enough even ever every everything eyes face fall family far
fast feel feeling fire first five for forever four free friend friends from full fun get girl girls give go god gold
gone good got great green had half hand hands happy hard has have he head hear heart heaven hell her here hey high him
his home hot house how i if in inside into is it its just keep kid kids kill king kiss know lady last late left let
lie life light like line little live living long look lord lost love low made make man many may me mind miss money
moon more morning most mother much music must my name need never new next nice night no not nothing now of off oh ok
old on once one only open or other our out over own paper party people place play please power queen rain real red
right rise river road rock room run sad said same say sea see she should show side silver sky sleep slow small so
some something song songs soul sound star stars start stay still stop story street summer sun sweet take talk tell
than that the their them then there these they thing things think this those three through time to today together
tonight too top town true try turn two under until up us very wait walk want war was water way we well were what when
where white who why wild will wind with without woman women world would yeah year years yes yesterday you young your
future ghost topic regard majestic hal kina zola lasso roar orochi
""".split())

# Words before a name that say "this is an artist": "songs by X", "music like X"
CUES_BEFORE = {"by", "like", "from", "similar to", "sounds like", "artists like", "songs like", "music like", "vibes like", "kind of like", "in the style of"}

# Words after a name that say the same: "X songs", "X vibes"
CUES_AFTER = {"songs", "song", "music", "vibes", "vibe", "type", "era", "playlist", "album", "albums", "radio", "mix", "core", "style", "fans"}

# Cues that ask for similar artists rather than the artist themselves
SIMILAR_CUES = {"like", "similar to", "sounds like", "artists like", "songs like", "music like", "vibes like", "kind of like", "in the style of"}

# How a genre can be named -> genres in the dataset. Phrases that are also
# common in everyday speech ("my soul", "at my house", "in a funk") need the
# word "music" or a more specific form.
GENRE_WORDS = {
    "hip hop": ["hip-hop"], "hiphop": ["hip-hop"], "rap": ["hip-hop"], "trap": ["hip-hop"],
    "r b": ["soul"], "r and b": ["soul"], "rnb": ["soul"], "randb": ["soul"], "neo soul": ["soul"], "soul music": ["soul"],
    "k pop": ["k-pop"], "kpop": ["k-pop"],
    "c pop": ["cantopop"], "cantopop": ["cantopop"],
    "pop": ["pop"], "pop music": ["pop"], "power pop": ["power-pop"],
    "indie": ["indie-pop", "alt-rock"], "indie pop": ["indie-pop"], "indie rock": ["alt-rock"],
    "rock": ["rock", "alt-rock", "hard-rock"], "alt rock": ["alt-rock"], "alternative": ["alt-rock"],
    "classic rock": ["rock", "hard-rock"], "hard rock": ["hard-rock"], "grunge": ["alt-rock"],
    "psychedelic": ["psych-rock"], "psych rock": ["psych-rock"], "rock n roll": ["rock-n-roll"], "rock and roll": ["rock-n-roll"],
    "punk": ["punk", "punk-rock"], "pop punk": ["punk-rock"], "emo": ["emo"],
    "metal": ["metal", "heavy-metal"], "heavy metal": ["heavy-metal"], "metalcore": ["metalcore"],
    "death metal": ["death-metal"], "black metal": ["black-metal"], "hardcore": ["hardcore"],
    "country": ["country"], "country music": ["country"], "folk": ["folk"], "folk music": ["folk"],
    "bluegrass": ["folk", "country"], "americana": ["folk", "country"],
    "jazz": ["jazz"], "blues": ["blues"], "gospel": ["gospel"], "funk music": ["funk"], "funky": ["funk"],
    "disco": ["disco"], "classical": ["classical"], "classical music": ["classical"], "orchestral": ["classical"],
    "opera": ["opera"], "piano": ["piano"], "piano music": ["piano"], "acoustic": ["acoustic"],
    "singer songwriter": ["singer-songwriter"], "ambient": ["ambient"], "new age": ["new-age"],
    "lofi": ["chill"], "lo fi": ["chill"],
    "edm": ["edm"], "electronic": ["electronic", "electro", "edm"], "electronic music": ["electronic", "electro", "edm"],
    "house music": ["house"], "deep house": ["deep-house"], "progressive house": ["progressive-house"],
    "techno": ["techno", "minimal-techno"], "trance": ["trance"], "dubstep": ["dubstep"],
    "drum and bass": ["drum-and-bass"], "dnb": ["drum-and-bass"], "hardstyle": ["hardstyle"],
    "trip hop": ["trip-hop"], "breakbeat": ["breakbeat"],
    "reggae": ["dub", "dancehall"], "dancehall": ["dancehall"], "ska": ["ska"],
    "afrobeat": ["afrobeat"], "afrobeats": ["afrobeat"], "salsa": ["salsa"], "samba": ["samba"], "tango": ["tango"],
    "forro": ["forro"], "sertanejo": ["sertanejo"],
    "bollywood": ["pop-film", "indian"], "indian music": ["indian"],
    "broadway": ["show-tunes"], "musicals": ["show-tunes"], "show tunes": ["show-tunes"], "musical theatre": ["show-tunes"],
    "musical theater": ["show-tunes"],
}

# Decades and parts of them -> (first year, last year)
DECADES = {
    "2000s": (2000, 2009), "00s": (2000, 2009), "early 2000s": (2000, 2004), "mid 2000s": (2003, 2007),
    "late 2000s": (2005, 2009), "y2k": (2000, 2003),
    "2010s": (2010, 2019), "early 2010s": (2010, 2014), "mid 2010s": (2013, 2017), "late 2010s": (2015, 2019),
    "2020s": (2020, 2023), "recent": (2020, 2023), "new music": (2021, 2023), "new songs": (2021, 2023),
    "latest": (2021, 2023),
}

# Decades the dataset doesn't have
OLDER_DECADES = {"50s": "1950s", "1950s": "1950s", "60s": "1960s", "1960s": "1960s", "70s": "1970s", "1970s": "1970s",
                 "80s": "1980s", "1980s": "1980s", "90s": "1990s", "1990s": "1990s"}

DATASET_YEARS = (2000, 2023)


# Phrases that introduce a song or artist to sound like: "songs like X", "the vibe of X"
STRONG_REFERENCE_CUES = [
    "songs like", "song like", "music like", "something like", "stuff like", "tracks like", "more like",
    "similar to", "sounds like", "sound like", "vibe of", "vibes of", "the vibe of", "same vibe as",
    "vibes like", "vibe like", "in the style of", "reminds me of", "kind of like", "inspired by",
]

# After these, "like" describes a feeling ("feel like a ghost"), not a song
LIKE_NOT_A_REFERENCE = {"feel", "feeling", "felt", "feels", "look", "looks", "looking", "seem", "seems", "act",
                        "acting", "sound", "something", "just", "it", "its", "i", "id", "would", "be", "is"}

# Words after a song or artist name: "cruel summer vibes", "drake type beat"
REFERENCE_AFTER = {"vibes", "vibe", "energy", "type beat", "type songs", "type music", "core", "era"}

# Words that end a reference: "songs like ribs but happier"
REFERENCE_STOP = {"but", "and", "for", "with", "when", "while", "because", "except", "or", "that", "which",
                  "please", "so", "only", "just", "to", "while", "if"}

MAX_REFERENCE_WORDS = 6


@dataclass
class Reference:
    """A song or artist the user wants music like, found in the description."""
    text: str                    # normalized words, e.g. "cruel summer"
    artist: str | None = None    # the "by X" part, if given
    kind: str = "like"           # "song": quoted or "X by Y"; "like": after a cue; "whole": the whole description;
                                 # "maybe": only mood words after a cue ("songs like flowers"): a song only if it's well known


@dataclass
class Entities:
    artists: list[str] = field(default_factory=list)    # names as in the dataset
    wants_similar: bool = False                         # "songs like X": similar artists, not only X
    genres: list[str] = field(default_factory=list)     # dataset genre names
    genre_labels: list[str] = field(default_factory=list)  # how the user said them, e.g. ["hip hop"]
    years: tuple[int, int] | None = None
    year_label: str | None = None                       # e.g. "2010s"
    notes: list[str] = field(default_factory=list)      # things Vibely couldn't do, said plainly
    references: list[Reference] = field(default_factory=list)  # songs/artists to sound like, not yet looked up


def normalize(text: str) -> str:
    """Lowercase, no accents, words separated by single spaces: "Beyoncé" -> "beyonce"."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"['’`]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


@lru_cache(maxsize=1)
def get_common_words() -> frozenset[str]:
    mood_words = {word for phrases in MOOD_TERMS.values() for phrase in phrases for word in phrase.split()}
    return frozenset(COMMON_WORDS | mood_words)


@lru_cache(maxsize=1)
def get_artist_index() -> dict[str, tuple[str, int]]:
    """{normalized name: (name as in the dataset, best popularity)} for every artist."""
    dataset = load_dataset()

    if dataset is None:
        return {}

    best = dataset.groupby("artist_name")["popularity"].max()
    index = {}

    for name, popularity in best.items():
        key = normalize(str(name))

        if not key or (key in index and index[key][1] >= popularity):
            continue

        index[key] = (str(name), int(popularity))

        # "the weeknd" can also be called "weeknd"
        if key.startswith("the ") and len(key) > 4:
            short = key[4:]
            if short not in index or index[short][1] < popularity:
                index[short] = (str(name), int(popularity))

    return index


def has_cue(words: list[str], start: int, end: int, used: list[bool]) -> tuple[bool, bool]:
    """Whether words[start:end] is marked as an artist by the words around it,
    and whether the cue asks for similar artists.

    Being listed with an artist found already counts as a cue too:
    in "drake and future", "future" is the artist Future.
    """
    before = " ".join(words[max(0, start - 3):start])
    after = words[end] if end < len(words) else ""

    next_to_artist = (
        (start >= 2 and words[start - 1] == "and" and used[start - 2])
        or (end + 1 < len(words) and words[end] == "and" and used[end + 1])
    )
    if next_to_artist:
        return True, False

    for cue in sorted(CUES_BEFORE, key=len, reverse=True):
        if before == cue or before.endswith(" " + cue):
            return True, cue in SIMILAR_CUES

    return after in CUES_AFTER, False


def is_recognizable(key: str, popularity: int, cued: bool) -> bool:
    """Whether a matched artist name should count, given how it was written."""
    words = key.split()
    common = get_common_words()

    # Names that are numbers or a mood phrase ("late night") are never artists without a cue
    if all(word.isdigit() for word in words):
        return False

    # Tiny everyday words ("the", "you") are never artist names, even with a cue
    if len(key) <= 3 and all(word in common for word in words):
        return False

    if cued:
        return popularity >= MIN_ARTIST_POPULARITY

    if all(word in common for word in words):
        return False

    needed = MIN_ONE_WORD_ARTIST_POPULARITY if len(words) == 1 else MIN_ARTIST_POPULARITY
    return popularity >= needed


def detect_artists(text: str) -> tuple[list[str], bool]:
    found, wants_similar, _ = detect_artist_spans(text)
    return found, wants_similar


def detect_artist_spans(text: str) -> tuple[list[str], bool, list[tuple[int, int, str]]]:
    """Artists named in the text, longest names first, and whether the user
    wants similar artists ("songs like X") rather than only X."""
    words = normalize(text).split()
    index = get_artist_index()
    used = [False] * len(words)
    found = []
    wants_similar = False
    spans = []

    # Twice: the second pass catches names listed with an artist found in the first
    for size in [*range(min(MAX_ARTIST_WORDS, len(words)), 0, -1), *range(min(MAX_ARTIST_WORDS, len(words)), 0, -1)]:
        for start in range(len(words) - size + 1):
            end = start + size

            if any(used[start:end]):
                continue

            key = " ".join(words[start:end])
            match = index.get(key)

            if not match:
                continue

            name, popularity = match
            cued, similar = has_cue(words, start, end, used)

            if not is_recognizable(key, popularity, cued):
                continue

            if name not in found:
                found.append(name)
            wants_similar = wants_similar or similar
            used[start:end] = [True] * size
            spans.append((start, end, name))

    return found, wants_similar, spans


def find_phrases(text: str, phrases) -> list[str]:
    """The phrases that appear in the text as whole words, longest first, without overlaps."""
    normalized = f" {normalize(text)} "
    found = []

    for phrase in sorted(phrases, key=len, reverse=True):
        marker = f" {phrase} "
        if marker in normalized:
            found.append(phrase)
            normalized = normalized.replace(marker, " | ")

    return found


def find_references(text: str, artist_spans: list[tuple[int, int, str]]) -> tuple[list[Reference], set[str]]:
    """Songs or artists the user wants music like, to be looked up.

    Also returns the names of found artists that are only there as a song's
    credit ("ribs by lorde" asks for songs like Ribs, not for Lorde's songs).
    """
    words = normalize(text).split()
    joined = " ".join(words)
    references: list[Reference] = []
    credited: set[str] = set()

    # Positions of found artists (a reference stops there) and of mood phrases
    # (a reference can include mood words, "cruel summer", but can't be only that)
    artist_at = [False] * len(words)
    for start, end, _ in artist_spans:
        artist_at[start:end] = [True] * (end - start)

    mood_at = [False] * len(words)
    for match in PHRASE_PATTERN.finditer(joined):
        first = len(joined[:match.start()].split())
        count = len(match.group().split())
        mood_at[first:first + count] = [True] * count

    common = get_common_words()

    def add(chunk: list[str], artist: str | None, kind: str):
        kind = "like" if kind == "plain" else kind
        chunk = chunk[:MAX_REFERENCE_WORDS]
        while chunk and chunk[-1] in REFERENCE_STOP:
            chunk = chunk[:-1]
        phrase = " ".join(chunk)
        if phrase and all(reference.text != phrase for reference in references):
            references.append(Reference(phrase, artist, kind))

    def is_only_mood(first: int, count: int) -> bool:
        return all(mood_at[first:first + count])

    # 1. Quoted titles: "cruel summer" (optionally followed by "by Artist")
    for match in re.finditer(r'["“”]([^"“”]{2,80})["“”](?:\s+by\s+([^,.!?;]{2,40}))?', text):
        add(normalize(match.group(1)).split(), normalize(match.group(2)) if match.group(2) else None, "song")

    # 2. "TITLE by ARTIST", where ARTIST is a found artist: "ribs by lorde"
    for start, end, name in artist_spans:
        if start >= 2 and words[start - 1] == "by":
            chunk = []
            for word in reversed(words[:start - 1]):
                if word in REFERENCE_STOP or word in {"like", "of", "as"} or len(chunk) >= MAX_REFERENCE_WORDS:
                    break
                chunk.insert(0, word)
            if chunk:
                add(chunk, name, "song")
                credited.add(name)

    def take_after(position: int) -> tuple[list[str], str | None, int]:
        """Words from `position` up to a stop word, a found artist, or "by".

        Returns (title words, the "by ..." artist text if any, where it ended).
        "sunflower by post malone" -> (["sunflower"], "post malone", ...) even
        when the dataset doesn't know Post Malone.
        """
        chunk, artist, index = [], None, position
        while index < len(words):
            if words[index] in REFERENCE_STOP or artist_at[index]:
                break
            if words[index] == "by":
                credit = []
                for after in range(index + 1, len(words)):
                    if words[after] in REFERENCE_STOP or len(credit) >= 4:
                        break
                    credit.append(words[after])
                artist = " ".join(credit) or None
                index += 1 + len(credit)
                break
            chunk.append(words[index])
            index += 1
        return chunk[:MAX_REFERENCE_WORDS], artist, index

    def add_list(position: int, kind: str):
        """References after a cue, including more joined by "and": "good 4 u and drivers license"."""
        while position < len(words):
            chunk, artist, end = take_after(position)
            if not chunk or has_title_after_by(position):
                return
            if is_only_mood(position, len(chunk)):
                if kind == "like":
                    add(chunk, artist, "maybe")
            elif kind == "like" or any(w not in common for w in chunk):
                add(chunk, artist, kind)
            if end < len(words) and words[end] == "and":
                position = end + 1
            else:
                return

    def has_title_after_by(position: int) -> bool:
        """Whether a "TITLE by ARTIST" from step 2 starts here (then it's handled already)."""
        return any(reference.kind == "song" and words[position:position + len(reference.text.split())] == reference.text.split()
                   for reference in references)

    # 3. After a cue: "songs like espresso", "the vibe of blinding lights"
    cue_positions = set()
    for cue in sorted(STRONG_REFERENCE_CUES, key=len, reverse=True):
        cue_words = cue.split()
        for index in range(len(words) - len(cue_words) + 1):
            if words[index:index + len(cue_words)] == cue_words and index not in cue_positions:
                cue_positions.update(range(index, index + len(cue_words)))
                add_list(index + len(cue_words), "like")

    # A plain "like", when it doesn't describe a feeling ("feel like a ghost")
    for index, word in enumerate(words):
        if word != "like" or index in cue_positions:
            continue
        if index > 0 and words[index - 1] in LIKE_NOT_A_REFERENCE:
            continue
        add_list(index + 1, "plain")

    # 4. Before "vibes"/"energy"/"type beat": "cruel summer vibes" (not when the
    # cue word is itself part of a mood phrase, like "main character energy")
    for index, word in enumerate(words):
        if mood_at[index] or not (word in REFERENCE_AFTER or " ".join(words[index:index + 2]) in REFERENCE_AFTER):
            continue
        chunk = []
        for back in range(index - 1, -1, -1):
            if words[back] in REFERENCE_STOP or artist_at[back] or words[back] in {"like", "of"} or len(chunk) >= 4:
                break
            chunk.insert(0, words[back])
        if chunk and any(w not in common for w in chunk) and not is_only_mood(index - len(chunk), len(chunk)):
            add(chunk, None, "like")

    # Drop references that are just an artist found already ("songs like phoebe bridgers")
    found_names = {normalize(name) for _, _, name in artist_spans}
    references = [reference for reference in references if reference.text not in found_names]

    return references, credited


def detect_entities(text: str) -> Entities:
    entities = Entities()

    entities.artists, entities.wants_similar, spans = detect_artist_spans(text)
    entities.references, credited = find_references(text, spans)

    # "ribs by lorde": Lorde is the song's artist, not a request for Lorde's songs
    for name in credited:
        if sum(1 for _, _, span_name in spans if span_name == name) == 1 and name in entities.artists:
            entities.artists.remove(name)

    for label in find_phrases(text, GENRE_WORDS):
        entities.genre_labels.append(label)
        for genre in GENRE_WORDS[label]:
            if genre not in entities.genres:
                entities.genres.append(genre)

    decades = find_phrases(text, DECADES)
    years = [int(year) for year in re.findall(r"\b(20[0-2][0-9])\b", text)]
    older = find_phrases(text, OLDER_DECADES)

    if decades:
        entities.years = DECADES[decades[0]]
        entities.year_label = decades[0]
    elif years:
        year = min(max(years[0], DATASET_YEARS[0]), DATASET_YEARS[1])
        entities.years = (year, year)
        entities.year_label = str(year)

    # A short description that's nothing but a name ("bad bunny", "espresso"):
    # look it up as a song or an artist
    words = normalize(text).split()
    has_anything = (
        entities.artists or entities.genres or entities.years or entities.references
        or PHRASE_PATTERN.search(" ".join(words))
    )
    if not has_anything and 0 < len(words) <= 5 and any(word not in get_common_words() for word in words):
        entities.references.append(Reference(" ".join(words), None, "whole"))

    if older and not entities.years:
        decade = OLDER_DECADES[older[0]]
        entities.notes.append(
            f"Vibely's song library only covers {DATASET_YEARS[0]}–{DATASET_YEARS[1]}, "
            f"so it can't pick songs from the {decade}."
        )

    return entities
