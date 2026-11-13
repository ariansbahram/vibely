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
- WebLLM (optional in-browser AI for understanding mood descriptions)
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
python3 dev_server.py
```

`dev_server.py` serves the frontend on port 5500 like `python3 -m http.server 5500`, but tells the browser not to cache, so changes show up on a normal refresh.

Then open http://127.0.0.1:5500 in the browser.

Use `127.0.0.1`, not `localhost`, so the login cookie is sent to the backend.

The backend only accepts browser requests from `http://127.0.0.1:5500` (CORS). If you serve the frontend somewhere else, set `FRONTEND_URL` in `.env` to match.

**The mood form** is the main box on the page. Describe the moment in your own words, for example "driving through San Francisco at night while feeling nostalgic", or click one of the examples under it, then press **Generate Playlist** (or ⌘/Ctrl + Enter). The form checks the description before sending it, using the same rules as the backend (3–500 characters, at least one letter), and shows what's wrong under the box. While it works, a progress card under **Recommended Songs** shows each step (understanding the mood, if smart mood understanding is on, then finding songs), how long it has taken, and a **Cancel** button; placeholder cards stand in for the songs on the first search, and on later searches the previous songs stay visible but faded until the new ones arrive. If a step runs long, a note explains why (for example, the first search after the backend starts is slower while the song library loads). After the songs load, it shows which mood words Vibely picked up on, or a tip if it didn't recognize any.

**Song cards** show each recommendation's rank, album cover, title (with an **E** badge if it's explicit), artists, album (when logged in), year, length, genre, tempo, and energy/mood/acoustic/danceable levels, plus how well it matches. **▶ Preview** plays the song right on the page in Spotify's embedded player: a 30-second preview, or the full song if you're logged in to Spotify in that browser (Spotify no longer gives new apps direct preview links). Only one preview plays at a time. **Open in Spotify**, or clicking the album cover, opens the song in Spotify.

**The playlist preview page** opens from **Review playlist →** under the results (address `#playlist`, so the browser's Back button works). It shows the playlist exactly as it will be saved: a cover made from the first album covers, the name (click to edit; the suggested name can be restored), the description, the number of songs, total length, and every song in its final order. You can:

- choose the order: **Best match first**, or **Smooth flow**, which arranges the songs so tempo, energy, and mood change gradually from one to the next (the best match stays first);
- move songs up or down with ↑ and ↓ (this makes it a custom order) and remove them with ✕;
- swap a song with ↻: it's replaced, in the same spot, by the best other song for the same mood;
- **Add songs**: after removing songs it offers to get back to the original size (e.g. "Add 3 songs (back to 10)"), otherwise it adds 5 more, up to 50. New songs keep the chosen order (re-sorted by match, or re-arranged for smooth flow);
- **Undo** the last removal or swap;
- **Save to Spotify**, which creates the playlist in exactly that order. After saving, the button shows **Saved ✓** until you change something; saving again creates a second playlist.

Logging in to Spotify from the preview page brings you back to it with the same songs and order.

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
| `POST` http://127.0.0.1:8000/playlists/order | Arrange songs in smooth-flow order (see [Playlists](#playlists)) |
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
  "understood_by": "keywords",
  "preferred_genres": [],
  "genre_affinity": {"acoustic": 1.0, "folk": 1.0, "indie-pop": 1.0, "jazz": 1.0, "piano": 0.5},
  "notes": [],
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
      "duration_ms": 274533,
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
| `vibe` | Optional, the in-browser AI's reading of the mood, see [Smart mood understanding](#smart-mood-understanding) |

`preferred_genres` lists the genres Vibely looked in first (see `MOOD_GENRES`; usually empty). `genre_affinity` says how well each genre suits the mood, 0–1 (see `GENRE_AFFINITY`), e.g. `{"folk": 1.0, "jazz": 1.0, "piano": 0.5}` for "rainy Sunday morning".

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

- `title`, `artists`, `genre`, `popularity`, `release_year`, `duration_ms` (length), and `spotify_url` (opens the song in Spotify).
- `score`: how well the song fits the mood, 0 to 1, shown as "% match". It combines:
  - **audio fit (60%)**: how close its tempo, energy, mood, acousticness, danceability, and instrumentalness are to the targets. 1.0 is exactly on target, 0.0 is as far off as a typical song. (Raw distance can't be used as-is: with 1.16M songs, dozens sit almost exactly on any target, so the top songs would all look like 96–97% matches and come from every genre at random.)
  - **genre fit (30%)**: how well the song's genre suits the mood (`genre_affinity`).
  - **popularity (10%)**: a small preference for songs people might know (full credit at Spotify popularity 60+).

  With no recognized mood words there's no genre opinion, so audio fit counts 85% and popularity 15%.
- Left out unless the request picks genres: live recordings (liveness above 0.8), spoken word (speechiness above 0.66), and comedy.
- For variety, one genre fills at most 40% of the playlist (`MAX_GENRE_SHARE` in `ranking.py`) unless there aren't enough songs from other fitting genres.
- `audio_features`: the song's tempo, energy, valence, etc. (same fields as `/audio-features`).
- `album_image_url`: the album artwork. When logged in to Spotify, `album` and `explicit` are filled in too; when logged out they are `null`, and the artwork comes from Spotify's public oEmbed endpoint instead.

How it works (`recommend_tracks()` in `services/recommender.py`): it scores every dataset song that passes the filters against the mood in one go, takes the best candidates, removes duplicates and applies `max_per_artist` with `rank_tracks()`, then looks up album details for the songs it returns (`services/track_details.py`). The first request after starting the backend takes a few seconds while the dataset loads; later ones take under a second.

The `mood` field is validated by the `RecommendationRequest` Pydantic model:

- required, and must be a string
- 3–500 characters after surrounding whitespace is removed
- must contain at least one letter (so `"!!!"` or `"12345"` are rejected)
- repeated spaces and line breaks are collapsed into single spaces

Invalid input returns `422` with a message saying what is wrong. If no song passes the filters, `recommendations` is an empty list.

#### More songs for the same mood

`POST /recommendations/more` returns new songs for the same description, e.g. to replace songs the user removed from the playlist. Send the same `mood` (and `vibe`, if smart mood understanding read it) as the `/recommendations` request. The backend works the mood out again the same way, without running the in-browser AI a second time, so the new songs fit the same mood, artists, genres, and years.

```json
{
  "mood": "sad taylor swift songs",
  "playlist_ids": ["<songs in the playlist now>"],
  "exclude_ids": ["<songs the user removed>"],
  "limit": 1
}
```

- New songs are never in `playlist_ids` or `exclude_ids`, and never another version of a song in the playlist (same title and main artist).
- `max_per_artist` (default 2) counts the whole playlist: an artist with two songs in `playlist_ids` gets no more. Artists the user named are exempt.
- With a named artist, the artist's share of the playlist is kept: swapping out one of their songs brings another of theirs.
- `limit` is 1–20 (default 1). The reply is `{"recommendations": [...]}`, best match first, in the same format as `/recommendations`; it's empty if no other songs pass.

#### Artists, genres, and years

Besides moods, `detect_entities()` in `services/entity_detection.py` finds what the description names outright, and `interpret_mood()` applies it:

| The user writes | Vibely picks up | The playlist |
|---|---|---|
| `taylor swift` | artist Taylor Swift | all Taylor Swift, best-known songs first (Anti-Hero, Don't Blame Me, cardigan...) |
| `sad taylor swift songs` | Taylor Swift + sad | half her songs that fit the mood, half similar-sounding songs from her genre (pop), mixed in between |
| `songs like phoebe bridgers` | Phoebe Bridgers, similar | a few of hers, mostly similar artists (Holly Humberstone, beabadoobee, Mitski...) |
| `drake and future for the gym` | Drake, Future + workout | both artists shared fairly, plus hip-hop from others |
| `chill jazz for studying` | genre jazz + chill, focused | jazz only (other genres only if no jazz fits) |
| `early 2010s throwbacks` | 2010–2014 + nostalgic | that era's hits (Wrecking Ball, Let Her Go, No Role Modelz...) |
| `90s rock` | rock + nostalgic | rock, with a note: the library only covers 2000–2023 |

- **Artists** are matched against the dataset's 64,000 artist names (accents and "the" optional: `beyonce`, `weeknd`). Only artists with a reasonably popular song count (Spotify popularity 45+, or 60+ for one-word names), so an obscure artist called "Sunday" doesn't match "rainy sunday". Names that are ordinary words ("King", "Future", "Ghost") need a cue: "songs by Future", "Ghost songs", or being listed with another artist ("drake and future").
- **Genres** use `GENRE_WORDS`, e.g. `hip hop`/`rap` → hip-hop, `r&b` → soul, `k-pop`, `country`, `indie`. Words that are common in everyday speech need a clearer form: "soul music" not "my soul", "house music" not "at my house".
- **Years**: decades (`2000s`, `early 2010s`, `y2k`), years (`2016`), and `recent`/`new music`. The dataset only has 2000–2023; earlier decades get a note instead.
- The response's `mood_terms` lists what was found (`["Taylor Swift", "sad"]`), `playlist_title` uses it ("Sad Taylor Swift Mix", "Chill Jazz Focus", "Early 2010s Nostalgic Vibes"), and `notes` explains anything Vibely couldn't do.

#### Songs and artists to sound like

Vibely also finds songs and artists the user wants music *like*, and looks them up: in the dataset first, then online through ReccoBeats for ones the dataset doesn't have (`services/music_lookup.py`).

| The user writes | Vibely finds | The playlist |
|---|---|---|
| `songs like cruel summer` | the song Cruel Summer (Taylor Swift) | songs that sound like it, from its genre; well-known songs count more; Cruel Summer itself is left out |
| `something like ribs by lorde but sadder` | Ribs (Lorde) + sad | songs like Ribs, nudged sadder (Lana Del Rey, Joji, Olivia Rodrigo...) |
| `songs like good 4 u and drivers license` | both songs | songs like both |
| `"espresso"`, `cruel summer vibes`, `the vibe of blinding lights` | the song | songs like it |
| `bad bunny` (not in the dataset) | Bad Bunny, online | songs that sound like Bad Bunny's music, in Spanish, starting with artists Bad Bunny works with that the dataset has (Arcángel, Tainy, Nio Garcia), with a note saying so |
| `chill songs like sunflower by post malone` | Sunflower (Post Malone), online | chill songs that sound like it |

- References are found after cues (`songs like`, `similar to`, `the vibe of`, `sounds like`, ...), in quotes, as `TITLE by ARTIST`, before `vibes`/`energy`/`type beat`, or as a short description that's only a name (`bad bunny`, `espresso`). A plain "like" counts only when it isn't describing a feeling: "feeling like a ghost" stays a mood.
- A name that could be a song or an artist goes to the more popular one. A title on its own goes to its most popular version, online or in the dataset ("espresso" is Sabrina Carpenter's, not an older song of the same name).
- Words in a found title don't count as moods: "songs like cruel summer" isn't "sunny".
- Online lookups send only the typed song or artist name to ReccoBeats. They take a few seconds the first time; results are cached until the server restarts. Online artists need a track with popularity 30+, so look-alike accounts don't match.

#### Languages

Songs are in **English unless the user asks otherwise** (`services/language.py`). The dataset has no language field, so each song's language is estimated:

1. The script: Hangul is Korean, kana Japanese, Cyrillic Russian, and so on.
2. For Latin script, common words and letters vote ("corazón", "não", "und", "aşk"; ñ, ã, ş, å).
3. Otherwise, a genre that's mostly one language decides (`k-pop` is Korean, `sertanejo` Portuguese), then a clearly English title, then the language of most of the artist's titles.

It's a heuristic: about 72% of the dataset comes out English, and an individual song can be wrong (for example, a romanized title from an artist who mostly sings in another language). Working it out takes ~30 s once; the result is saved to `backend/data/song_languages.npz` and reused.

Which languages are allowed:

| The user writes | Languages |
|---|---|
| `rainy sunday morning` | English |
| `sad spanish songs`, `songs in french`, `bollywood`, `k-pop party` | only the language asked for (shown as e.g. "Sad Spanish Vibes") |
| `international chill songs`, `any language` | any |
| `songs like bts`, `bad bunny`, `songs like tití me preguntó` | the language of the artists, songs, or genres named (Korean, Spanish) |
| `canciones tristes para llorar` | the language the description is written in (Spanish) |

Songs by artists the user named are never filtered out by language. If no songs pass, any language is used.

#### Mood terms

`extract_mood_terms()` in `services/mood_analysis.py` finds the meaningful terms in the description and returns them in the order they appear:

```python
extract_mood_terms("Nostalgic late-night drive in the rain")
# ["nostalgic", "late night", "road trip", "rainy"]
```

- It knows 56 terms (feelings, energy level, time/weather/seasons, places and activities) and about 870 words and phrases that signal them, including slang (`in my feels` gives `sad`, `villain era` gives `rebellious`, `delulu` gives `dreamy`). For example `studying`, `finals`, and `lock in` all give `focused`. To teach it a new word, add it to `MOOD_TERMS`; a new term also needs targets in `MOOD_TARGETS` and a title word in `playlist_title.py`.
- Intensity words change how much a term counts: `"a little sad but very excited"` counts `sad` at half weight and `excited` at 1.5×, so the songs lean excited. `extract_weighted_mood_terms()` returns these weights, and `get_target_features()` accepts them.
- Case, punctuation, and hyphens are ignored, and only whole words match (`train` does not give `rainy`).
- A term right after a negation is skipped: `"not sad, just tired"` gives `["sleepy"]`.
- A description with no known words gives an empty list.

#### Smart mood understanding

The word lists only know the words someone added. For everything else (niche, specific, or mixed descriptions like "my cat knocked my coffee off the table and I'm laughing"), the frontend can use a small AI model that runs in the browser with [WebLLM](https://github.com/mlc-ai/web-llm). It is free, needs no API key, and the description doesn't leave the computer for this step.

- **Downloading:** on someone's first visit, the model (`Qwen2.5-1.5B-Instruct`, `MODEL_ID` in `frontend/js/vibe-ai.js`) starts downloading by itself, about 1 GB, with a progress bar under the mood box. Vibely works with its built-in mood words in the meantime. The browser keeps the model, so later visits load it in a few seconds.
  - It doesn't download by itself on a data-saver or slow (3G or slower) connection, or on a device that reports less than 4 GB of memory. There, the panel offers **Turn it on** instead.
  - **Stop and don't download** (during the download) and **Turn off** (afterwards) are remembered, so it doesn't download again on the next visit. **Turn it on** brings it back.
  - To delete the downloaded model: in Chrome on the Vibely page, DevTools → Application → Storage → Clear site data.
- **Requirements:** a browser with WebGPU (recent Chrome, Edge, or Safari on a computer) and about 1.6 GB of graphics memory. Otherwise the panel says so and Vibely uses the word lists.
- **Speed:** reading a description takes about 6–13 seconds on an older Intel MacBook; faster on newer computers.
- **What it sends:** `vibe-ai.js` asks the model for a level (`very_low` to `very_high`) for each audio feature, 1–4 mood words, up to 3 genres from the dataset's list, and a playlist title. WebLLM's JSON mode makes the model's answer fit that shape. The frontend sends it as `vibe` with the request:

```json
{
  "mood": "my cat knocked my coffee off the table and I'm laughing",
  "vibe": {
    "moods": ["amused", "playful", "silly"],
    "energy": "medium", "valence": "very_high", "tempo": "medium",
    "acousticness": "medium", "danceability": "medium", "instrumentalness": "low",
    "genres": [],
    "title": "Cat Chaos Morning"
  }
}
```

- **How the backend uses it** (`interpret_mood()` in `services/mood_interpretation.py`): the levels become numbers (`medium` = 0.5, tempo `fast` = 128 BPM). The AI's mood words are also run through the word lists, so `"playful"` brings in the hand-tuned `playful` targets. For features a known mood has a target for, the AI's value and the hand-tuned one are averaged (the hand-tuned one counts more, 70%, when the user's own words name a known mood); for the rest, the AI's value is used. Genres from a known mood (see `MOOD_GENRES`) beat the AI's genre guesses. The AI's title becomes `playlist_title`, and `understood_by` is `"ai"`.
- **If anything goes wrong** (model still loading, slow answer, unusable answer, or the backend rejects the `vibe`), the request is sent without `vibe`, and the word lists are used as before.

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
- Some moods are about a style of music more than its numbers, so `MOOD_GENRES` also limits them to fitting genres: `fairytale` (knights, princesses, castles) to `classical`, `opera`, `show-tunes`; `rave` to techno, house, EDM, and trance; `tavern` (medieval, pirates, sea shanties) to `folk`; `meditative` to `ambient`, `new-age`, `sleep`; `worship` to `gospel`. A genre filter in the request takes priority, and if the preferred genres leave no songs (for example with an artist filter), any genre is used.
- `create_target_vector()` returns the same targets as a NumPy vector in the same feature order as `create_song_vector()`.

#### Mood vector

`create_mood_vector()` in `services/mood_vector.py` does both steps at once: it takes the description, finds the mood terms, and returns the target vector. The attributes and their order match `create_song_vector()` (energy, tempo, valence, acousticness, danceability, instrumentalness):

```python
create_mood_vector("something energetic for the gym")
# array([0.91, 140.0, 0.6, 0.075, 0.7, 0.1])
```

`create_scaled_mood_vector()` returns the same vector on the 0–1 scale used by `create_scaled_song_vector()`, so a mood and a song can be compared directly.

#### Similarity scores

> `POST /recommendations` no longer ranks by these scores alone; it uses `get_fit_scores()` in `services/recommender.py`, which adds genre fit and popularity (see the `score` field above). The functions below are still available for comparing songs by sound only.

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
- In the frontend, **Save to Spotify** on the playlist preview page calls this endpoint with the songs in the order shown there and the playlist name at the top of the page. The name starts as the suggested `playlist_title` and can be changed; **Use suggested name** puts the suggestion back, and an empty name saves with the suggestion.

`POST /playlists/order` returns the same songs in smooth-flow order (no login needed, nothing is saved). It uses `order_track_ids()` in `services/ordering.py` (see [Playlist order](#playlist-order)) with audio features from the dataset; songs without features go at the end and are listed in `unordered_ids`. At most 100 songs; 50 take under a second.

```bash
curl -X POST http://127.0.0.1:8000/playlists/order -H "Content-Type: application/json" -d '{"track_ids": ["6cdKPAK7e6DiiQXvdyi86d", "398KEejceOUqgLi5HqSh8v", "0Rb8NUbVXhzoNB69Hl1U4G"]}'
```

```json
{
  "track_ids": ["6cdKPAK7e6DiiQXvdyi86d", "398KEejceOUqgLi5HqSh8v", "0Rb8NUbVXhzoNB69Hl1U4G"],
  "transition_scores": [0.9639, 0.9588],
  "unordered_ids": []
}
```

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
│   ├── mood_interpretation.py # interpret_mood(): word lists + optional in-browser AI vibe -> targets, genres, title
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
│   ├── recommender.py         # recommend_tracks(): target features -> ranked dataset songs (used by POST /recommendations)
│   └── track_details.py       # add_track_details(): album, artwork, explicit flag from Spotify or oEmbed
└── utils/dependencies.py      # get_spotify_client() / get_optional_spotify_client(): Spotify client from the session cookie

backend/data/spotify_data.csv  # Kaggle dataset (not in git, see Setup step 5)

frontend/
├── index.html                 # the page: mood form, results, playlist saving
├── css/styles.css
└── js/
    ├── app.js                 # form checks, calls the backend, shows songs, saves playlists
    └── vibe-ai.js             # smart mood understanding: in-browser AI (WebLLM) that reads the mood
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
| The page looks half-styled or out of date after an update (e.g. "Best match firstSmooth flow" run together as plain text) | The browser is using old copies of the files. Serve the frontend with `python3 dev_server.py` instead of `python3 -m http.server`, then hard-refresh once: ⌘+Shift+R on Mac, Ctrl+Shift+R on Windows. |
| After logging in, the app says "Couldn't connect to Spotify." | Check `SPOTIFY_CLIENT_SECRET` and that `SPOTIFY_REDIRECT_URI` matches the Dashboard exactly. |
