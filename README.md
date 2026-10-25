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

```bash
python3 -m venv .venv
```

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

Do not commit `.env` to GitHub.

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

## Backend URLs

| URL | Description |
|---|---|
| http://127.0.0.1:8000/docs | FastAPI documentation |
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/auth/login | Log in with Spotify |
| http://127.0.0.1:8000/me | Current Spotify user's ID, display name, and email (log in first) |
| http://127.0.0.1:8000/search?q=blinding%20lights | Search Spotify tracks by song, artist, or keyword (log in first) |

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
    "spotify_url": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"
  }
]
```

Spotify filters work inside `q`, for example `q=track:blinding lights artist:the weeknd` or `q=artist:taylor swift`.

## Project Structure

```
backend/app/
├── main.py                    # FastAPI app and router registration
├── models/track.py            # Track model (id, title, artists, album, spotify_url)
├── routes/
│   ├── auth.py                # /auth/login, /auth/callback
│   ├── user.py                # /me
│   └── search.py              # /search
├── services/
│   ├── spotify_auth.py        # Spotify OAuth setup (tokens kept in memory, not in a .cache file)
│   ├── token_store.py         # In-memory login sessions
│   ├── spotify_user.py        # get_user_profile()
│   └── spotify_search.py      # search_tracks()
└── utils/dependencies.py      # get_spotify_client(): logged-in Spotify client from the session cookie
```

## Audio Features (Planned)

Spotify no longer provides audio features (energy, valence, tempo, etc.) to new apps, so Vibely will use:

1. **[ReccoBeats API](https://api.reccobeats.com/v1/audio-features)** (main source): free, no API key, accepts Spotify track IDs, up to date. Example: `https://api.reccobeats.com/v1/audio-features?ids=0VjIjW4GlUZAMYd2vXMi3b`. The newest releases may be missing.
2. **[Spotify_1Million_Tracks](https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks)** Kaggle dataset (backup, tracks up to 2023) for when ReccoBeats is unavailable or has no data.

Fetched features will be saved so each track is only looked up once. Do not commit the dataset CSV; download it into `backend/data/`.

## Spotify Access

The Vibely Spotify app is in Development Mode, so only accounts added by the app owner can log in. If login fails with "The user is not registered for this application", ask the app owner to add your Spotify account email under **Settings → User Management** in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).

## Troubleshooting

| Problem | Fix |
|---|---|
| `zsh: command not found: python` | Use `python3` (macOS has no `python` command). |
| `pydantic_core` fails to build during `pip install` | Your Python is 3.14. Recreate the venv with Python 3.11–3.13, e.g. `python3.11 -m venv .venv`. |
| `zsh: command not found: uvicorn` | The wrong venv is active. Activate the one in the project root (`vibely/.venv`), not a new one inside `backend/`. |
| Login or `/me` shows "Internal Server Error" | Usually your Spotify account isn't registered for the app. See [Spotify Access](#spotify-access). |
| `/me` or `/search` says "Not logged in to Spotify." | The backend restarted. Log in again at `/auth/login`. |
