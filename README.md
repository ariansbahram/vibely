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

## Backend Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate

1. Clone the repository
git clone <repository-url>
cd vibely

2. Create a virtual environment
python -m venv .venv

Activate it:
Ubuntu / WSL / macOS
source .venv/bin/activate

Windows PowerShell
.\.venv\Scripts\Activate.ps1

3. Install backend dependencies
pip install -r backend/requirements.txt

Environment Variables
Create a .env file in the root of the project:
vibely/.env

Add:
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/auth/callback

Do not commit .env to GitHub.

The Spotify Developer Dashboard redirect URI must also be:
http://127.0.0.1:8000/auth/callback

Running the Backend
Open a terminal and run:
cd ~/vibely
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload

The backend runs at:
http://127.0.0.1:8000

FastAPI documentation:
http://127.0.0.1:8000/docs

Health check:
http://127.0.0.1:8000/health

Spotify login:
http://127.0.0.1:8000/auth/login

Running the Frontend
Keep the backend running.

Open a second terminal and run:
cd ~/vibely/frontend
python -m http.server 5500

The frontend runs at:
http://127.0.0.1:5500

Running the Full Application
You need two terminals.
Terminal 1 — Backend
cd ~/vibely
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload

Backend:
http://127.0.0.1:8000

Terminal 2 — Frontend
cd ~/vibely/frontend
python -m http.server 5500

Frontend:
http://127.0.0.1:5500

Then open:
http://127.0.0.1:5500

in the browser.
