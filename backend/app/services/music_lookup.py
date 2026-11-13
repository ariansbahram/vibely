"""Look up songs and artists the user names: in the song dataset first, then
online through ReccoBeats (free, no login) for ones the dataset doesn't have.

  find_song("cruel summer")   -> Cruel Summer by Taylor Swift, with its sound
  find_external_artist("bad bunny") -> Bad Bunny's sound, language, and the
                                       artists they work with that the dataset has

Online lookups send the typed name to ReccoBeats. Results are cached, so a
name is looked up once per server run.
"""

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

from app.services.dataset import load_dataset
from app.services.entity_detection import get_artist_index, normalize
from app.services.feature_vector import RECOMMENDATION_FEATURES
from app.services.language import ENGLISH, get_artist_language, get_song_languages, get_text_language
from app.services.ranking import normalize_title
from app.services.roccobeats import (
    get_artist_tracks,
    get_audio_features,
    search_artists,
    search_tracks,
    spotify_id,
)

# A song in the dataset needs this popularity to be recognized from its title
# alone; less popular songs share titles with better-known ones
MIN_SONG_POPULARITY = 40

# Online, an artist's best track needs this popularity, so look-alike
# accounts ("Bad Bunnys") don't win over the real artist
MIN_EXTERNAL_POPULARITY = 30

# How many of an artist's tracks to average for their sound
TRACKS_FOR_SOUND = 10


@dataclass
class SongSeed:
    """A song the user named, to find songs like it."""
    title: str
    artist: str
    track_id: str                       # Spotify ID
    target_features: dict[str, float]   # its sound
    genre: str | None = None            # from the dataset, if it's there
    language: str = ENGLISH
    popularity: int = 0


@dataclass
class ExternalArtist:
    """An artist the dataset doesn't have, looked up online."""
    name: str
    target_features: dict[str, float]
    language: str = ENGLISH
    collaborators: list[str] = field(default_factory=list)   # artists they work with that the dataset has
    popularity: int = 0                                       # their best track's


@lru_cache(maxsize=1)
def get_title_index() -> dict[str, list[int]]:
    """{normalized title: dataset row numbers} ("Anti-Hero - Remix" -> "anti hero")."""
    index: dict[str, list[int]] = {}

    for row, title in enumerate(load_dataset()["track_name"].astype(str)):
        index.setdefault(normalize_title(title), []).append(row)

    return index


def get_features(row) -> dict[str, float]:
    return {feature: float(row[feature]) for feature in RECOMMENDATION_FEATURES}


@lru_cache(maxsize=256)
def find_song(title: str, artist: str | None = None) -> SongSeed | None:
    """A song by title (and artist, if given): from the dataset, or else online.

    With only a title, the more popular version wins: "espresso" is Sabrina
    Carpenter's 2024 hit (online), not an older song of the same name in the dataset.
    """
    in_dataset = find_dataset_song(title, artist)

    if in_dataset and artist:
        return in_dataset

    online = find_external_song(title, artist)

    if in_dataset and online:
        return online if online.popularity > in_dataset.popularity else in_dataset

    return in_dataset or online


def find_dataset_song(title: str, artist: str | None) -> SongSeed | None:
    dataset = load_dataset()
    rows = get_title_index().get(normalize_title(title), [])

    if not rows:
        return None

    songs = dataset.iloc[rows]

    if artist:
        songs = songs[songs["artist_name"].map(normalize) == normalize(artist)]
    else:
        songs = songs[songs["popularity"] >= MIN_SONG_POPULARITY]

    if songs.empty:
        return None

    best = songs.sort_values("popularity", ascending=False).iloc[0]
    languages, codes = get_song_languages()

    return SongSeed(
        title=str(best["track_name"]),
        artist=str(best["artist_name"]),
        track_id=str(best.name),
        target_features=get_features(best),
        genre=str(best["genre"]),
        language=codes[languages[dataset.index.get_loc(best.name)]],
        popularity=int(best["popularity"]),
    )


def find_external_song(title: str, artist: str | None) -> SongSeed | None:
    wanted_title = normalize_title(title)

    # With an artist, look through their tracks: title search doesn't always find
    # a song ("Sunflower - Spider-Man: Into the Spider-Verse" by Post Malone)
    if artist:
        _, results, _ = find_artist_tracks(artist)
    else:
        results = search_tracks(title, size=15)

    matches = [
        track for track in results
        if normalize_title(track.get("trackTitle", "")) == wanted_title
        and (not artist or any(normalize(a["name"]) == normalize(artist) for a in track.get("artists", [])))
    ]

    if not matches:
        return None

    best = max(matches, key=lambda track: track.get("popularity") or 0)

    if not artist and (best.get("popularity") or 0) < MIN_EXTERNAL_POPULARITY:
        return None

    track_id = spotify_id(best["href"])
    features = get_audio_features([track_id]).get(track_id)

    if not features:
        return None

    artist_name = best["artists"][0]["name"] if best.get("artists") else (artist or "")

    # The title's own words, else the artist's language (online if the dataset lacks them)
    language = get_text_language(best["trackTitle"])
    if not language:
        if normalize(artist_name) in get_artist_index():
            language = get_artist_language(get_artist_index()[normalize(artist_name)][0])
        else:
            external = find_external_artist(artist_name)
            language = external.language if external else ENGLISH

    return SongSeed(
        title=best["trackTitle"],
        artist=artist_name,
        track_id=track_id,
        target_features={feature: float(getattr(features, feature)) for feature in RECOMMENDATION_FEATURES},
        genre=get_main_genre(artist_name),
        language=language,
        popularity=int(best.get("popularity") or 0),
    )


def get_main_genre(artist: str) -> str | None:
    """The dataset genre most of an artist's songs are in, if the dataset has them."""
    dataset = load_dataset()
    songs = dataset[dataset["artist_name"] == artist]
    return None if songs.empty else str(songs["genre"].mode().iloc[0])


@lru_cache(maxsize=256)
def find_artist_tracks(name: str) -> tuple[str, list[dict], int]:
    """An artist's tracks online: (their name, tracks, best track's popularity).

    Several accounts can share a name ("Bad Bunny"); the real artist is the one
    with the most popular tracks.
    """
    wanted = normalize(name)
    candidates = [artist for artist in search_artists(name) if normalize(artist["name"]) == wanted][:3]

    best_name, best_tracks, best_popularity = name, [], -1
    for candidate in candidates:
        tracks = [
            track for track in get_artist_tracks(candidate["id"], size=50)
            if any(artist.get("id") == candidate["id"] for artist in track.get("artists", []))
        ]
        popularity = max((track.get("popularity") or 0 for track in tracks), default=0)

        if popularity > best_popularity:
            best_name, best_tracks, best_popularity = candidate["name"], tracks, popularity

    return best_name, best_tracks, max(best_popularity, 0)


@lru_cache(maxsize=256)
def find_external_artist(name: str) -> ExternalArtist | None:
    """An artist the dataset doesn't have: their sound, language, and collaborators."""
    wanted = normalize(name)
    display_name, best_tracks, best_popularity = find_artist_tracks(name)

    if best_popularity < MIN_EXTERNAL_POPULARITY:
        return None

    top = sorted(best_tracks, key=lambda track: track.get("popularity") or 0, reverse=True)[:TRACKS_FOR_SOUND]
    features = list(get_audio_features([spotify_id(track["href"]) for track in top]).values())

    if not features:
        return None

    target = {
        feature: round(sum(getattr(song, feature) for song in features) / len(features), 3)
        for feature in RECOMMENDATION_FEATURES
    }

    # Language from all their titles together
    language = get_text_language(" ".join(track["trackTitle"] for track in top), min_votes=2) or ENGLISH

    # Artists they work with that the dataset has, most frequent first
    index = get_artist_index()
    together = Counter(
        index[normalize(artist["name"])][0]
        for track in top
        for artist in track.get("artists", [])
        if normalize(artist["name"]) != wanted and normalize(artist["name"]) in index
    )

    return ExternalArtist(
        name=display_name,
        target_features=target,
        language=language,
        collaborators=[artist for artist, _ in together.most_common(4)],
        popularity=best_popularity,
    )
