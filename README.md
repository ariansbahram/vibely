# Vibely

Vibely is a mood-based Spotify playlist recommendation application developed for CS122.

Users can enter detailed moods or situations, and Vibely will recommend songs with musical characteristics that match the requested atmosphere.

## Tech Stack

- Python
- FastAPI
- Spotify Web API / Spotipy
- Pandas
- NumPy
- scikit-learn
- HTML/CSS
- JavaScript
- Tailwind CSS

## Setup

### Requirements

- Python 3.11–3.13 (3.14 is not supported yet; `pydantic_core` fails to install)
- A Spotify account that has been added to the Vibely app (see [Spotify Access](#spotify-access))

Check your version with `python3 --version`. If it prints 3.14, use `python3.11` (or another supported version) in the commands below.

### 1. Clone the repository

```bash
git clone <repository-url>
cd vibely
```

### 2. Create and activate a virtual environment

Only do this once, from the project root (not inside `backend/`):

```bash
python3.11 -m venv .venv
```

If the venv already exists, skip this step and just activate it. Running `venv` again with a different Python mixes two versions into the same environment.

macOS / Linux / WSL:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Add environment variables

Copy `.env.example` to `.env` in the project root and fill in the values:

```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/auth/callback
```

The redirect URI in the Spotify Developer Dashboard must also be `http://127.0.0.1:8000/auth/callback`.

Optional: `FRONTEND_URL` is where the frontend runs (default `http://127.0.0.1:5500`). After logging in, users are sent back there, and it's the only site allowed to call the backend from a browser.

Do not commit `.env` to GitHub.

### 5. Download the dataset (optional)

The backup source for audio features is the [Spotify_1Million_Tracks](https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks) dataset (~1.16M tracks from 2000–2023, 176 MB).

1. Sign in to Kaggle (free) and click **Download** on the dataset page.
2. Unzip it and put the CSV at `backend/data/spotify_data.csv`:

   ```bash
   mkdir -p backend/data
   unzip ~/Downloads/archive.zip -d backend/data/
   ```

`backend/data/` is in `.gitignore`. Do not commit the CSV (GitHub rejects files over 100 MB). The backend still runs without it; only the dataset backup is skipped.

## Running the App

You need two terminals.

**Terminal 1 — Backend**

```bash
cd ~/vibely
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend**

```bash
cd ~/vibely/frontend
python3 -m http.server 5500
```

Then open http://127.0.0.1:5500 in the browser.

Use `127.0.0.1`, not `localhost`, so the login cookie is sent to the backend.

The backend only accepts browser requests from `http://127.0.0.1:5500` (CORS). If you serve the frontend somewhere else, set `FRONTEND_URL` in `.env` to match.

**Connect Spotify** takes you to Spotify's login page and then back to the app, which shows "Connected to Spotify." and changes the button to "Connected as <your name>". Songs already on screen are kept through the login, so you can generate songs first and connect when you want to save them.

## Backend URLs

| URL | Description |
|---|---|
| http://127.0.0.1:8000/docs | FastAPI documentation |
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/auth/login | Log in with Spotify, then return to the frontend with `?spotify=connected`, `denied`, or `error` |
| http://127.0.0.1:8000/me | Current Spotify user's ID, display name, and email (log in first) |
| http://127.0.0.1:8000/search?q=blinding%20lights | Search Spotify tracks by song, artist, or keyword (log in first) |
| http://127.0.0.1:8000/audio-features?ids=0VjIjW4GlUZAMYd2vXMi3b | Audio features (energy, valence, tempo, etc.) for up to 100 comma-separated Spotify track IDs |

| `POST` http://127.0.0.1:8000/recommendations | Submit a mood or situation description (see [Recommendations](#recommendations)) |
| `POST` http://127.0.0.1:8000/playlists | Save songs as a new playlist in the user's Spotify account (log in first, see [Playlists](#playlists)) |

Logins are stored in memory, so restarting the backend (including auto-reload on save) logs everyone out.

### Search

`GET /search?q=<query>&limit=<1-10>` returns up to 10 tracks (Spotify's limit for Development Mode apps):

```json
[
  {
    "id": "0VjIjW4GlUZAMYd2vXMi3b",
    "title": "Blinding Lights",
    "artists": ["The Weeknd"],
    "album": "After Hours",
    "album_image_url": "https://i.scdn.co/image/ab67616d0000b273...",
    "spotify_url": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b",
    "genre": null,
    "explicit": false,
    "popularity": 90,
    "release_year": 2020
  }
]
```

Spotify filters work inside `q`, for example `q=track:blinding lights artist:the weeknd` or `q=artist:taylor swift`.

### Recommendations

`POST /recommendations` takes the user's mood or situation as JSON and returns matching songs from the Kaggle dataset, best match first. No login is needed, but the dataset must be downloaded (Setup step 5); without it the endpoint returns `503`.

```bash
curl -X POST http://127.0.0.1:8000/recommendations -H "Content-Type: application/json" -d '{"mood": "rainy Sunday morning, studying with coffee", "limit": 1}'
```

```json
{
  "mood": "rainy Sunday morning, studying with coffee",
  "mood_terms": ["rainy", "morning", "focused"],
  "target_features": {
    "energy": 0.383,
    "tempo": 95.0,
    "valence": 0.475,
    "acousticness": 0.583,
    "danceability": 0.55,
    "instrumentalness": 0.8
  },
  "playlist_title": "Rainy Morning Focus",
  "recommendations": [
    {
      "id": "6cdKPAK7e6DiiQXvdyi86d",
      "title": "It Only Has To Happen Once",
      "artists": ["Nels Cline"],
      "album": null,
      "album_image_url": "https://image-cdn-fa.spotifycdn.com/image/ab67616d00001e02a6871835eef5ff1cc6c78bef",
      "spotify_url": "https://open.spotify.com/track/6cdKPAK7e6DiiQXvdyi86d",
      "genre": "guitar",
      "explicit": null,
      "popularity": 6,
      "release_year": 2016,
      "score": 0.9745,
      "audio_features": {
        "track_id": "6cdKPAK7e6DiiQXvdyi86d",
        "acousticness": 0.593,
        "danceability": 0.566,
        "energy": 0.329,
        "instrumentalness": 0.806,
        "liveness": 0.133,
        "loudness": -18.559,
        "speechiness": 0.0298,
        "tempo": 97.436,
        "valence": 0.454,
        "key": 1,
        "mode": 1
      }
    }
  ]
}
```

| Request field | Meaning |
|---|---|
| `mood` | Required. The mood or situation in the user's own words |
| `limit` | How many songs to return, 1–50 (default 10) |
| `max_per_artist` | Most songs by one artist (default 2); `null` for no limit |
| `filters` | Optional, see [Filters](#filters) |

`playlist_title` is a suggested name for the playlist, built from the mood terms by `generate_playlist_title()` in `services/playlist_title.py`:

| Mood description | Suggested title |
|---|---|
| rainy Sunday morning, studying with coffee | Rainy Morning Focus |
| nostalgic late-night drive in the rain | Nostalgic Late Night Road Trip |
| sad and lonely | Sad & Lonely Vibes |
| studying | Focus Mix |
| something for my wedding (no known mood terms) | Something for my wedding |

A title is: one feeling word (two joined with `&` if there's nothing else), then the time of day, then the activity, or `Vibes` if there's no activity. Each mood term's title word is listed in `DESCRIBE_WORDS`, `WHEN_WORDS`, and `WHAT_WORDS`; a new mood term needs an entry in one of them. Without any known mood terms, the description itself is used, shortened to about 50 characters.

Each song in `recommendations` has:

- `title`, `artists`, `genre`, `popularity`, `release_year`, and `spotify_url` (opens the song in Spotify).
- `score`: how close the song is to the mood's target features, from 0 to 1 (Euclidean, see [Similarity scores](#similarity-scores)).
- `audio_features`: the song's tempo, energy, valence, etc. (same fields as `/audio-features`).
- `album_image_url`: the album artwork. When logged in to Spotify, `album` and `explicit` are filled in too; when logged out they are `null`, and the artwork comes from Spotify's public oEmbed endpoint instead.

How it works (`recommend_tracks()` in `services/recommender.py`): it scores every dataset song that passes the filters against the mood in one go, takes the best candidates, removes duplicates and applies `max_per_artist` with `rank_tracks()`, then looks up album details for the songs it returns (`services/track_details.py`). The first request after starting the backend takes a few seconds while the dataset loads; later ones take under a second.

The `mood` field is validated by the `RecommendationRequest` Pydantic model:

- required, and must be a string
- 3–500 characters after surrounding whitespace is removed
- must contain at least one letter (so `"!!!"` or `"12345"` are rejected)
- repeated spaces and line breaks are collapsed into single spaces

Invalid input returns `422` with a message saying what is wrong. If no song passes the filters, `recommendations` is an empty list.

#### Mood terms

`extract_mood_terms()` in `services/mood_analysis.py` finds the meaningful terms in the description and returns them in the order they appear:

```python
extract_mood_terms("Nostalgic late-night drive in the rain")
# ["nostalgic", "late night", "road trip", "rainy"]
```

- It knows 27 terms (feelings, energy level, time and weather, activities), each with a list of words and phrases that signal it, e.g. `studying`, `homework`, and `coding` all give `focused`. To teach it a new word, add it to `MOOD_TERMS`.
- Case, punctuation, and hyphens are ignored, and only whole words match (`train` does not give `rainy`).
- A term right after a negation is skipped: `"not sad, just tired"` gives `["sleepy"]`.
- A description with no known words gives an empty list.

#### Target features

`get_target_features()` in `services/mood_targets.py` turns the mood terms into the audio features a matching song should have. `MOOD_TARGETS` lists what each term points to, for example:

| Term | Target |
|---|---|
| `energetic` | high energy (0.90), fast tempo (140 BPM), danceable, not acoustic |
| `sad` | low valence (0.15), low energy, moderately acoustic (0.60), slow tempo (85 BPM) |
| `nostalgic` | lowish valence (0.40), moderate energy and acousticness (0.50), 100 BPM |
| `focused` | mostly instrumental (0.80), low energy |

- A term only sets the features it has an opinion about.
- With several terms, each feature is the average of the terms that mention it, so `["energetic", "sad"]` gives energy 0.60.
- A feature that no term mentions gets a neutral value close to the dataset's middle (energy 0.65, tempo 120, valence 0.45, acousticness 0.30, danceability 0.55, instrumentalness 0.10). With no terms at all, every feature is neutral.
- `create_target_vector()` returns the same targets as a NumPy vector in the same feature order as `create_song_vector()`.

#### Mood vector

`create_mood_vector()` in `services/mood_vector.py` does both steps at once: it takes the description, finds the mood terms, and returns the target vector. The attributes and their order match `create_song_vector()` (energy, tempo, valence, acousticness, danceability, instrumentalness):

```python
create_mood_vector("something energetic for the gym")
# array([0.91, 140.0, 0.6, 0.075, 0.7, 0.1])
```

`create_scaled_mood_vector()` returns the same vector on the 0–1 scale used by `create_scaled_song_vector()`, so a mood and a song can be compared directly.

#### Similarity scores

`score_tracks()` in `services/similarity.py` compares a mood description against candidate tracks (a list of `AudioFeatures`) and returns a score for each one, best match first:

```python
score_tracks("something energetic for the gym", candidates)
# {"gym_banger": 0.9972, "mid_pop": 0.9714, "study_lofi": 0.6556, "slow_acoustic": 0.4799}
```

It uses scikit-learn's `cosine_similarity` on the scaled vectors by default. Pass `metric="euclidean"` to score by straight-line distance instead (1.0 is identical, 0.0 is as far apart as possible).

| Metric | What it compares | Notes |
|---|---|---|
| `cosine` (default) | The balance between features (direction of the vector) | Scores bunch up near the top: the typical dataset song scores about 0.9 against a gym mood. |
| `euclidean` | How close every feature is to its target | In testing on the full dataset, its top matches were closer to the target values. |

`calculate_similarity_scores()` is the lower-level scoring function: it takes an already-scaled mood vector and a matrix of scaled song vectors, so it can score the whole dataset at once (about 0.2 s for 1.16M songs).

#### Ranking

`rank_tracks()` in `services/ranking.py` takes candidate tracks and their scores and returns the top matches, best first, each with its `score`:

```python
rank_tracks(tracks, scores, limit=10, max_per_artist=2)
```

- `limit` is the most tracks to return (default 10).
- `max_per_artist` is optional. With `max_per_artist=2`, no artist appears on more than two returned tracks; every artist listed on a track counts, including featured ones. Leave it out for no restriction.
- Duplicates are removed. A track ID is used once, and so is each song: tracks with the same main artist and the same title are treated as one song, ignoring anything in brackets or after a ` - ` (so `Blinding Lights`, `Blinding Lights - Remastered`, and `Blinding Lights (Live)` are one song). The highest-scoring version is kept.
- Tracks without a score are left out.

#### Playlist order

`order_tracks()` in `services/ordering.py` rearranges the recommended tracks so the playlist flows, instead of playing them strictly from highest to lowest score:

```python
order_tracks(tracks, features)  # features: {track_id: AudioFeatures}
```

- The first track stays first, so the playlist opens with the best match.
- From there, each song is followed by the most similar song not used yet. A second pass then tries small changes (reversing a stretch of the order, or moving one song elsewhere) and keeps each one that raises the playlist's total transition score. The result is close to the best possible order, not guaranteed to be it: on 40 test sets of 8 songs it found the best order 34 times.
- Neighbors are compared the same way `transition_score()` compares two songs (see below).
- The same tracks come back; only the order changes. Tracks without audio features go at the end.
- `get_playlist_transition_scores(tracks, features)` returns the transition score between each pair of neighbors, for checking or displaying how well a playlist flows.

On 20 random dataset songs, the average change between neighbors dropped from 29 to 17 BPM in tempo, from 0.32 to 0.16 in energy, and from 0.42 to 0.15 in valence; the average transition score rose from 0.70 to 0.85.

#### Transition score

`transition_score()` in `services/ordering.py` rates how smoothly one song leads into another, from 0 to 1:

```python
transition_score(track_a, track_b)                        # two AudioFeatures
transition_score(track_a, track_b, {"tempo": 1.0, "energy": 1.0})  # choose the attributes
```

- `1.0` means the songs are identical on every compared attribute; `0.0` means they are as different as possible on all of them. The order doesn't matter.
- By default it compares the attributes in `TRANSITION_WEIGHTS`, after scaling: tempo (weight 2), energy (1), valence (1), acousticness (0.5), and danceability (0.5). Tempo counts double because the scale covers 30–250 BPM while most songs sit between 80 and 165.
- Pass your own weights to compare other attributes. Any of the six recommendation features can be used.
- For reference, two random dataset songs typically score about 0.77; two similar gym tracks score about 0.97, and a gym track into a slow acoustic song about 0.56.

#### Filters

The request can include an optional `filters` object to narrow down which songs may be recommended. Every filter is optional:

```json
{
  "mood": "rainy Sunday morning, studying with coffee",
  "filters": {
    "genres": ["indie-pop", "folk"],
    "artists": ["Phoebe Bridgers"],
    "allow_explicit": false,
    "min_popularity": 30,
    "max_popularity": 90,
    "min_year": 2010,
    "max_year": 2023
  }
}
```

| Filter | Keeps tracks that... |
|---|---|
| `genres` | are in one of the listed genres (`Hip Hop` and `hip-hop` are the same) |
| `artists` | have one of the listed artists, including as a featured artist |
| `allow_explicit` | `false` keeps only tracks known to be clean (needs a Spotify login on `/recommendations`, otherwise `401`); `true` (default) keeps everything |
| `min_popularity`, `max_popularity` | have a Spotify popularity (0–100) inside the range |
| `min_year`, `max_year` | were released inside the range (1900–2100) |

- A filter that is left out, or an empty `genres`/`artists` list, restricts nothing.
- A `min` greater than its `max`, or a value outside the allowed range, returns `422`.
- `filter_tracks()` in `services/filters.py` applies the filters to a list of tracks. It reads the optional `genre`, `explicit`, `popularity`, and `release_year` fields on `Track`.
- A track that is missing the detail a filter needs is left out. This matters because the two sources know different things: Spotify search provides `explicit`, `popularity`, and `release_year` but no genre; the Kaggle dataset has genre, popularity, and year but no explicit flag.

### Playlists

`POST /playlists` creates a new playlist in the logged-in user's Spotify account and adds the songs to it, in the order given. It needs a Spotify login; without one it returns `401`.

```bash
curl -X POST http://127.0.0.1:8000/playlists -b "vibely_session=<your session cookie>" -H "Content-Type: application/json" -d '{"name": "Vibely: rainy Sunday morning", "track_ids": ["0VjIjW4GlUZAMYd2vXMi3b"]}'
```

```json
{
  "id": "3cEYpjA9oz9GiPac4AsH4n",
  "name": "Vibely: rainy Sunday morning",
  "spotify_url": "https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n",
  "track_count": 1
}
```

| Request field | Meaning |
|---|---|
| `name` | Required, 1–100 characters |
| `track_ids` | Required, 1–500 Spotify track IDs (the `id` of each recommendation). A song listed twice is added once |
| `description` | Optional, up to 300 characters |
| `public` | `true` shows the playlist on the user's profile; `false` (default) keeps it private |

- `create_playlist()` in `services/spotify_playlists.py` uses Spotipy's `current_user_playlist_create()` and `playlist_add_items()`, adding songs 100 at a time (Spotify's limit per request).
- If Spotify rejects the songs after creating the playlist, the empty playlist is removed again and the request fails.
- `403` usually means the login is missing the playlist permissions (log in again) or, while the Spotify app is in Development Mode, the user isn't on the app's list of allowed users in the Spotify Developer Dashboard.
- In the frontend, **Save to Spotify** (under the recommendations) calls this endpoint with the songs currently shown and the name in the **Playlist name** box. The box starts with the suggested `playlist_title` and can be changed; **Use suggested name** puts the suggestion back, and an empty box saves with the suggestion.

## Project Structure

```
backend/app/
├── main.py                    # FastAPI app and router registration
├── models/
│   ├── track.py               # Track model (id, title, artists, spotify_url, plus optional album, album_image_url, genre, explicit, popularity, release_year)
│   ├── audio_features.py      # AudioFeatures model (energy, valence, tempo, etc.)
│   ├── recommendation.py      # RecommendationRequest (validated mood text), RecommendationFilters, RecommendedTrack, RecommendationResponse
│   └── playlist.py            # PlaylistRequest, PlaylistResponse
├── routes/
│   ├── auth.py                # /auth/login, /auth/callback
│   ├── user.py                # /me
│   ├── search.py              # /search
│   ├── features.py            # /audio-features
│   ├── recommendations.py     # POST /recommendations
│   └── playlists.py           # POST /playlists
├── services/
│   ├── spotify_auth.py        # Spotify OAuth setup (tokens kept in memory, not in a .cache file)
│   ├── token_store.py         # In-memory login sessions
│   ├── spotify_user.py        # get_user_profile()
│   ├── spotify_search.py      # search_tracks()
│   ├── spotify_playlists.py   # create_playlist(): new playlist in the user's account, songs added
│   ├── playlist_title.py      # generate_playlist_title(): suggested playlist name from the mood terms
│   ├── roccobeats.py          # get_audio_features(): ReccoBeats API (main source)
│   ├── dataset.py             # get_dataset_features(): Kaggle CSV lookup (backup)
│   ├── feature_lookup.py      # get_features_with_backup(): ReccoBeats, then dataset
│   ├── mood_analysis.py       # extract_mood_terms(): mood terms in a description
│   ├── mood_targets.py        # get_target_features(): mood terms -> target audio features
│   ├── mood_vector.py         # create_mood_vector(): description -> target vector
│   ├── similarity.py          # score_tracks(): similarity score for each candidate track
│   ├── ranking.py             # rank_tracks(): top matches, no duplicates, optional artist limit
│   ├── filters.py             # filter_tracks(): genre, artist, explicit, popularity, release year
│   ├── ordering.py            # order_tracks(): smooth transitions between consecutive tracks
│   ├── recommender.py         # recommend_tracks(): mood -> ranked dataset songs (used by POST /recommendations)
│   └── track_details.py       # add_track_details(): album, artwork, explicit flag from Spotify or oEmbed
└── utils/dependencies.py      # get_spotify_client() / get_optional_spotify_client(): Spotify client from the session cookie

backend/data/spotify_data.csv  # Kaggle dataset (not in git, see Setup step 5)
```

## Audio Features

Spotify no longer provides audio features (energy, valence, tempo, etc.) to new apps, so `/audio-features` uses two sources:

1. **[ReccoBeats API](https://api.reccobeats.com/v1/audio-features)** (main source): free, no API key, accepts Spotify track IDs (max 40 per request; the backend batches larger lists). Covers older and recent songs, but the newest releases may be missing. In testing it had about 80% of the dataset's tracks.
2. **[Spotify_1Million_Tracks](https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks)** dataset (backup): used for tracks ReccoBeats doesn't have, or for everything if ReccoBeats is down. Covers 2000–2023. Loaded on first use (~1–2 s), then lookups are instant.

Example response:

```json
{
  "features": [
    {"track_id": "0VjIjW4GlUZAMYd2vXMi3b", "energy": 0.73, "valence": 0.334, "tempo": 171.001, "...": "..."}
  ],
  "from_dataset": ["1kXiPFjU226OQuMhMe2VFB"],
  "missing": ["11hcBLPtbMp4aQI6zGQLub"]
}
```

- `from_dataset`: tracks whose features came from the dataset instead of ReccoBeats.
- `missing`: tracks found in neither source (usually very new releases).

Planned: save fetched features so each track is only looked up once.

## Spotify Access

The Vibely Spotify app is in Development Mode, so only accounts added by the app owner can log in. If login fails with "The user is not registered for this application", ask the app owner to add your Spotify account email under **Settings → User Management** in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

## Troubleshooting

| Problem | Fix |
|---|---|
| `zsh: command not found: python` | Use `python3` (macOS has no `python` command). |
| `pydantic_core` fails to build during `pip install` | Your Python is 3.14. Recreate the venv with Python 3.11–3.13, e.g. `python3.11 -m venv .venv`. |
| `pip install` works but the backend says `No module named ...` | `pip` and `python` in the venv point to different Python versions (happens if `venv` was run twice). Check with `head -1 .venv/bin/pip`; if it isn't 3.11, rebuild: `python3.11 -m venv --clear .venv && pip install -r backend/requirements.txt`. |
| `zsh: command not found: uvicorn` | The wrong venv is active. Activate the one in the project root (`vibely/.venv`), not a new one inside `backend/`. |
| Login or `/me` shows "Internal Server Error" | Usually your Spotify account isn't registered for the app. See [Spotify Access](#spotify-access). |
| `/me` or `/search` says "Not logged in to Spotify.", or the app says "Connect Spotify first" after you connected | The backend restarted. Click **Connect Spotify** again. |
| After logging in, the app says "Couldn't connect to Spotify." | Check `SPOTIFY_CLIENT_SECRET` and that `SPOTIFY_REDIRECT_URI` matches the Dashboard exactly. |
