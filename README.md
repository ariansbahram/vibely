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

Logins are stored in memory, so restarting the backend (including auto-reload on save) logs everyone out.

## Spotify Access

The Vibely Spotify app is in Development Mode, so only accounts added by the app owner can log in. If login fails with "The user is not registered for this application", ask the app owner to add your Spotify account email under **Settings → User Management** in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
