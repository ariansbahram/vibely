"""Work out what music a mood description calls for.

Two sources, combined when both are there:

- The word lists (mood_analysis.py, mood_targets.py): hand-tuned targets for
  56 known moods. Reliable, but only for words someone thought to add.
- The in-browser AI's reading (a Vibe, sent by the frontend): understands any
  description, however niche or mixed, but a small model is vague with numbers
  and tends to call everything "medium".

The AI's mood words are run through the word lists too, so "rave in a berlin
warehouse" -> AI says "energetic" -> the hand-tuned "energetic" targets apply.
"""

import re
from dataclasses import dataclass, field, replace

from app.models.recommendation import Vibe
from app.services.dataset import load_dataset
from app.services.entity_detection import Entities, detect_entities, get_common_words, normalize
from app.services.language import (
    ENGLISH,
    GENRE_LANGUAGES,
    LANGUAGE_NAMES,
    get_artist_language,
    get_language_mask,
    get_requested_languages,
    get_text_language,
)
from app.services.music_lookup import ExternalArtist, SongSeed, find_external_artist, find_song
from app.services.feature_vector import RECOMMENDATION_FEATURES
from app.services.mood_analysis import extract_weighted_mood_terms
from app.services.mood_targets import MOOD_TARGETS, get_genre_affinity, get_preferred_genres, get_target_features
from app.services.playlist_title import DESCRIBE_WORDS, generate_playlist_title

# What the AI's levels mean as numbers
LEVEL_VALUES = {"very_low": 0.1, "low": 0.3, "medium": 0.5, "high": 0.7, "very_high": 0.9}
TEMPO_VALUES = {"very_slow": 70.0, "slow": 90.0, "medium": 110.0, "fast": 128.0, "very_fast": 145.0}

# For a feature the known moods have a target for, how much the AI's level counts
# (the rest comes from the hand-tuned targets). Features no known mood mentions
# come from the AI alone.
AI_WEIGHT = 0.5

# Lower when the user's own words name a known mood ("rave"): then the
# hand-tuned targets are a sure thing and the AI's vaguer levels count less
AI_WEIGHT_WITH_KNOWN_WORDS = 0.3

# How much of the playlist comes from artists the user named:
#   just the artist ("taylor swift")          -> all of it
#   artist and a mood ("sad taylor swift")    -> half, the rest similar-sounding songs
#   similar artists ("songs like taylor swift") -> a few, mostly similar artists
ARTIST_ONLY_SHARE = 1.0
ARTIST_WITH_MOOD_SHARE = 0.5
SIMILAR_ARTISTS_SHARE = 0.3

# Where a decade's or year's hits mostly are, for "2010s throwbacks"
ERA_HIT_GENRES = ["pop", "dance", "hip-hop", "edm", "indie-pop", "rock"]

# A song only named with mood words ("songs like flowers") counts if it's this well known
MIN_MAYBE_SONG_POPULARITY = 75

# Fewer songs than this in a requested language gets a note
FEW_SONGS = 300

# How genre names are shown, when it isn't just capitalizing
GENRE_DISPLAY = {
    "hip hop": "hip-hop", "hiphop": "hip-hop", "r b": "R&B", "r and b": "R&B", "rnb": "R&B", "randb": "R&B",
    "k pop": "K-pop", "kpop": "K-pop", "c pop": "C-pop", "lo fi": "lo-fi", "lofi": "lo-fi", "edm": "EDM", "dnb": "drum and bass",
    "rock n roll": "rock 'n' roll",
}


@dataclass
class MoodInterpretation:
    mood_terms: list[str]                # what Vibely understood, shown to the user
    target_features: dict[str, float]    # what the songs should sound like
    preferred_genres: list[str]          # genres to look in first; empty for any
    genre_affinity: dict[str, float]     # how well each genre suits the mood, 0–1
    playlist_title: str
    understood_by: str                   # "ai" or "keywords"

    # Artists the user named, and how much of the playlist should be theirs (0–1)
    featured_artists: list[str] = field(default_factory=list)
    artist_share: float = 0.0

    # Release years the user asked for, e.g. (2010, 2019) for "2010s"
    year_range: tuple[int, int] | None = None

    # Things Vibely couldn't do, said plainly ("no songs from the 1990s")
    notes: list[str] = field(default_factory=list)

    # Languages the songs should be in; None for any. English unless the user
    # asked for or named something in another language.
    languages: list[str] | None = field(default_factory=lambda: [ENGLISH])

    # Songs never to recommend: the ones the user named ("songs like Cruel Summer")
    exclude_ids: list[str] = field(default_factory=list)

    # How songs are scored: None (normal), "era" (decades: hits count more),
    # or "reference" (songs like a named song or artist: well-known songs count more)
    fit_profile: str | None = None


def interpret_mood(mood: str, vibe: Vibe | None = None) -> MoodInterpretation:
    """The targets, genres, artists, years, and title for a description,
    using the AI's vibe if given."""
    entities = detect_entities(mood)
    seeds, external_artists, lookup_notes = resolve_references(entities)
    entities.notes.extend(lookup_notes)

    # Words in a song's title aren't moods: "songs like cruel summer" isn't "sunny"
    mood_words = remove_found_names(mood, seeds, external_artists, entities)

    interpretation = interpret_mood_words(mood_words, vibe)
    has_mood_words = bool(extract_weighted_mood_terms(mood_words))
    interpretation = apply_entities(interpretation, entities, has_mood_words, seeds, external_artists)

    if seeds or external_artists:
        interpretation.fit_profile = "reference"
    elif entities.years:
        interpretation.fit_profile = "era"

    interpretation.languages, language_notes, language_labels = get_allowed_languages(
        mood, interpretation, entities, seeds, external_artists,
    )
    interpretation.notes.extend(language_notes)

    # "Spanish" in what Vibely picked up on, and in the title ("Sad Spanish Vibes")
    if language_labels:
        interpretation.mood_terms = [*language_labels, *interpretation.mood_terms]
        if not (seeds or external_artists or entities.artists or entities.genres):
            terms = list(extract_weighted_mood_terms(mood_words))
            interpretation.playlist_title = generate_playlist_title(mood_words, terms, " ".join(language_labels))

    return interpretation


def remove_found_names(
    mood: str,
    seeds: list[SongSeed],
    external_artists: list[ExternalArtist],
    entities: Entities,
) -> str:
    """The description without the song titles and artist names found in it."""
    text = f" {normalize(mood)} "

    names = [normalize(seed.title) for seed in seeds] + [normalize(seed.artist) for seed in seeds]
    names += [normalize(artist.name) for artist in external_artists]

    for name in sorted(filter(None, names), key=len, reverse=True):
        text = text.replace(f" {name} ", " ")

    return text.strip()


def resolve_references(entities: Entities) -> tuple[list[SongSeed], list[ExternalArtist], list[str]]:
    """Look up the songs and artists the user wants music like.

    "songs like cruel summer" -> the song; "bad bunny" (not in the dataset) ->
    the artist, online. When a name could be either, the more popular one wins.
    """
    seeds, artists, notes = [], [], []

    for reference in entities.references:
        song, artist = None, None

        if reference.kind == "song" or reference.artist:
            song = find_song(reference.text, reference.artist)
        elif reference.kind == "maybe":
            found = find_song(reference.text)
            song = found if found and found.popularity >= MIN_MAYBE_SONG_POPULARITY else None
        else:
            song = find_song(reference.text)
            artist = find_external_artist(reference.text)

            if song and artist:
                # A tie goes to the artist when the name is all the user typed
                if song.popularity > artist.popularity or (song.popularity == artist.popularity and reference.kind != "whole"):
                    artist = None
                else:
                    song = None

        if song and all(seed.track_id != song.track_id for seed in seeds):
            seeds.append(song)
        elif artist and all(found.name != artist.name for found in artists):
            artists.append(artist)
            notes.append(
                f"{artist.name} isn't in Vibely's song library, so these are songs that sound like their music."
            )
        elif not song and not artist and reference.kind not in ("maybe", "whole"):
            if any(word not in get_common_words() for word in reference.text.split()):
                notes.append(f'Vibely couldn\'t find a song or artist called "{reference.text}".')

    return seeds, artists, notes


def get_allowed_languages(
    mood: str,
    interpretation: MoodInterpretation,
    entities: Entities,
    seeds: list[SongSeed],
    external_artists: list[ExternalArtist],
) -> tuple[list[str] | None, list[str], list[str]]:
    """The languages songs may be in, notes about them, and labels to show.

    - Asked for ("sad spanish songs"): only those. "International": any.
    - Named artists, songs, or genres: their languages ("songs like bad bunny"
      is Spanish, "songs like bts" Korean, "taylor swift and bts" both).
    - Written in another language ("canciones tristes"): that language.
    - Otherwise: English.
    """
    requested, _ = get_requested_languages(mood)
    notes, labels = [], []

    if requested is None:
        return None, notes, labels

    if requested:
        labels = [LANGUAGE_NAMES.get(language, language) for language in requested]
        available = int(get_language_mask(set(requested)).sum())
        if available < FEW_SONGS:
            notes.append(f"Vibely's song library has only a few {' and '.join(labels)} songs, so some may be in other languages.")
        return requested, notes, labels

    named = set()
    named.update(get_artist_language(artist) for artist in entities.artists)
    named.update(seed.language for seed in seeds)
    named.update(artist.language for artist in external_artists)
    named.update(GENRE_LANGUAGES[genre] for genre in entities.genres if genre in GENRE_LANGUAGES)

    written_in = get_text_language(mood, min_votes=2)
    if written_in and written_in != ENGLISH:
        named.add(written_in)

    return sorted(named or {ENGLISH}), notes, labels


def interpret_mood_words(mood: str, vibe: Vibe | None = None) -> MoodInterpretation:
    """The targets, genres, and title from the mood words (and the AI's vibe)."""
    known_terms = extract_weighted_mood_terms(mood)

    if vibe is None:
        terms = list(known_terms)

        return MoodInterpretation(
            mood_terms=terms,
            target_features=get_target_features(known_terms),
            preferred_genres=get_preferred_genres(terms),
            genre_affinity=get_genre_affinity(known_terms),
            playlist_title=generate_playlist_title(mood, terms),
            understood_by="keywords",
        )

    # The AI's mood words are plainer than the user's ("bittersweet", "energetic"),
    # so they often match known moods the description itself didn't.
    # The user's own words go last, so their intensity ("a little sad") wins.
    ai_weight = AI_WEIGHT_WITH_KNOWN_WORDS if known_terms else AI_WEIGHT

    ai_terms = extract_weighted_mood_terms(", ".join(vibe.moods))
    known_terms = {**ai_terms, **known_terms}

    targets = blend_targets(get_ai_targets(vibe), known_terms, ai_weight)

    # Hand-picked genres for a known mood beat the AI's guesses
    terms = list(known_terms)
    genres = get_preferred_genres(terms) or list(vibe.genres)

    return MoodInterpretation(
        mood_terms=list(vibe.moods),
        target_features=targets,
        preferred_genres=genres,
        genre_affinity=get_genre_affinity(known_terms, list(vibe.genres)),
        playlist_title=vibe.title or generate_playlist_title(mood, terms),
        understood_by="ai",
    )


def get_ai_targets(vibe: Vibe) -> dict[str, float]:
    """The AI's levels as numbers, e.g. energy "high" -> 0.7, tempo "fast" -> 128 BPM."""
    return {
        feature: TEMPO_VALUES[vibe.tempo] if feature == "tempo" else LEVEL_VALUES[getattr(vibe, feature)]
        for feature in RECOMMENDATION_FEATURES
    }


def blend_targets(
    ai_targets: dict[str, float],
    known_terms: dict[str, float],
    ai_weight: float = AI_WEIGHT,
) -> dict[str, float]:
    """Average the AI's targets with the hand-tuned ones, feature by feature.

    Only features a known mood has an opinion about are averaged; for the rest
    the AI's value is used as is (the hand-tuned "neutral" value would just
    pull everything toward the middle).
    """
    curated = get_target_features(known_terms)
    blended = {}

    for feature in RECOMMENDATION_FEATURES:
        mentioned = any(feature in MOOD_TARGETS.get(term, {}) for term in known_terms)

        if mentioned:
            value = ai_weight * ai_targets[feature] + (1 - ai_weight) * curated[feature]
        else:
            value = ai_targets[feature]

        blended[feature] = round(value, 3)

    return blended


def apply_entities(
    interpretation: MoodInterpretation,
    entities: Entities,
    has_mood_words: bool,
    seeds: list[SongSeed] | None = None,
    external_artists: list[ExternalArtist] | None = None,
) -> MoodInterpretation:
    """Add the artists, genres, and years the user named to a mood interpretation.

    What the user names outright beats what Vibely guessed from the mood:
    a named genre replaces the mood's genres, and named artists pull the
    sound toward theirs.
    """
    targets = dict(interpretation.target_features)
    affinity = dict(interpretation.genre_affinity)
    preferred = list(interpretation.preferred_genres)
    share = 0.0

    # Genres the user named: look there first, and they fit fully
    if entities.genres:
        preferred = list(entities.genres)
        for genre in entities.genres:
            affinity[genre] = 1.0

    if entities.artists:
        artist_targets, artist_genres = get_artist_profile(entities.artists)

        if artist_targets:
            if has_mood_words or entities.genres:
                # Meet in the middle: the artist's sound, nudged toward the mood
                targets = {
                    feature: round((targets[feature] + artist_targets[feature]) / 2, 3)
                    for feature in RECOMMENDATION_FEATURES
                }
            else:
                targets = artist_targets
                affinity = {}   # no mood to fit: the artist's genres decide alone

        # The other songs come from the artist's genres ("drake" -> hip-hop),
        # unless the user named genres. The mood's genres still help, at half weight.
        if not entities.genres and artist_genres:
            affinity = {genre: round(value / 2, 3) for genre, value in affinity.items()}
            for genre in artist_genres:
                affinity[genre] = 1.0
            preferred = list(artist_genres)

        if entities.wants_similar:
            share = SIMILAR_ARTISTS_SHARE
        elif has_mood_words or entities.genres:
            share = ARTIST_WITH_MOOD_SHARE
        else:
            share = ARTIST_ONLY_SHARE

    # Songs and missing artists to sound like ("songs like cruel summer", "bad bunny")
    seeds = seeds or []
    external_artists = external_artists or []
    featured = list(entities.artists)

    if seeds or external_artists:
        sounds = [seed.target_features for seed in seeds] + [artist.target_features for artist in external_artists]
        reference_targets = {
            feature: round(sum(sound[feature] for sound in sounds) / len(sounds), 3)
            for feature in RECOMMENDATION_FEATURES
        }

        if has_mood_words or entities.genres or entities.artists:
            targets = {feature: round((targets[feature] + reference_targets[feature]) / 2, 3) for feature in RECOMMENDATION_FEATURES}
        else:
            targets = reference_targets
            affinity = {}

        # Their genres: the songs' own, and the genres of artists a missing artist works with
        collaborators = [name for artist in external_artists for name in artist.collaborators]
        _, collaborator_genres = get_artist_profile(collaborators) if collaborators else (None, [])
        reference_genres = [seed.genre for seed in seeds if seed.genre] + collaborator_genres

        if not entities.genres and reference_genres:
            affinity = {genre: round(value / 2, 3) for genre, value in affinity.items()}
            for genre in reference_genres:
                affinity[genre] = 1.0
            preferred = list(dict.fromkeys(reference_genres))

        # A missing artist's collaborators stand in for them, as similar artists
        if collaborators and not entities.artists:
            featured = list(dict.fromkeys(collaborators))
            share = SIMILAR_ARTISTS_SHARE

    # "Early 2010s throwbacks" means that era's hits, which are mostly in these genres
    if entities.years and not entities.genres and not entities.artists:
        for genre in ERA_HIT_GENRES:
            affinity[genre] = max(affinity.get(genre, 0), 0.8)

    genre_labels = [GENRE_DISPLAY.get(label, label) for label in entities.genre_labels]

    found = [
        *[f"{short_title(seed.title)} ({seed.artist})" for seed in seeds],
        *[artist.name for artist in external_artists],
        *entities.artists,
        *genre_labels,
        *([entities.year_label] if entities.year_label else []),
    ]

    return replace(
        interpretation,
        mood_terms=[*found, *interpretation.mood_terms],
        target_features=targets,
        preferred_genres=preferred,
        genre_affinity=affinity,
        playlist_title=get_title(interpretation, entities, genre_labels, seeds, external_artists),
        featured_artists=featured,
        artist_share=share,
        year_range=entities.years,
        notes=[*interpretation.notes, *entities.notes],
        exclude_ids=[seed.track_id for seed in seeds],
    )


def short_title(title: str) -> str:
    """"Sunflower - Spider-Man: Into the Spider-Verse" -> "Sunflower"."""
    return title.split(" - ")[0].strip() or title


def get_artist_profile(artists: list[str]) -> tuple[dict[str, float] | None, list[str]]:
    """The artists' average sound (target features) and their main genres."""
    dataset = load_dataset()

    if dataset is None:
        return None, []

    songs = dataset[dataset["artist_name"].isin(artists)]

    if songs.empty:
        return None, []

    targets = {feature: round(float(songs[feature].mean()), 3) for feature in RECOMMENDATION_FEATURES}

    # Each artist's genres that cover at least a quarter of their songs
    genres = []
    for _, artist_songs in songs.groupby("artist_name"):
        shares = artist_songs["genre"].value_counts(normalize=True)
        for genre, part in shares.items():
            if part >= 0.25 and genre not in genres:
                genres.append(genre)

    return targets, genres


def get_title(
    interpretation: MoodInterpretation,
    entities: Entities,
    genre_labels: list[str],
    seeds: list[SongSeed] = (),
    external_artists: list[ExternalArtist] = (),
) -> str:
    """A playlist title that mentions the songs, artists, or genre the user named."""
    # The first feeling word from the mood, e.g. "Sad" for "sad taylor swift songs"
    terms = list(extract_weighted_mood_terms(", ".join(interpretation.mood_terms)))
    feeling = next((DESCRIBE_WORDS[term] for term in terms if term in DESCRIBE_WORDS), None)

    if seeds or external_artists:
        names = " & ".join([*[short_title(seed.title) for seed in seeds], *[artist.name for artist in external_artists]][:2])
        return f"Songs Like {names}"[:100]

    if entities.artists:
        names = " & ".join(entities.artists[:2])

        if entities.wants_similar:
            return f"Songs Like {names}"[:100]

        return " ".join(part for part in [feeling, names, "Mix"] if part)[:100]

    if genre_labels:
        genre_word = genre_labels[0]
        genre_word = genre_word if genre_word[0].isupper() else genre_word.title()
        title = generate_playlist_title("", terms, genre_word)
    else:
        title = interpretation.playlist_title

    # "Early 2010s Nostalgic Vibes", "2016 Summer Vibes"
    if entities.year_label:
        label = entities.year_label.replace("y2k", "Y2K")
        label = label[0].upper() + label[1:]
        title = f"{label} {title}"

    return title[:100]
