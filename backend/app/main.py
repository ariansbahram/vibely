from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.spotify_auth import FRONTEND_URL
from app.routes.auth import router as auth_router
from app.routes.user import router as user_router
from app.routes.search import router as search_router
from app.routes.features import router as audio_features_router
from app.routes.recommendations import router as recommendations_router
from app.routes.playlists import router as playlists_router




app = FastAPI(
    title="Vibely API",
    description="Backend API for Vibely",
    version="1.0.0",
)

# The frontend runs on a different port (see "Running the App" in the README),
# so the browser only lets it call this API if the API allows that origin.
# allow_credentials lets the login cookie come along.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(search_router)
app.include_router(audio_features_router)
app.include_router(recommendations_router)
app.include_router(playlists_router)


@app.get("/")
def root():
    return {"message": "Welcome to Vibely!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
