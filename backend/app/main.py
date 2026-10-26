from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.user import router as user_router
from app.routes.search import router as search_router
from app.routes.features import router as audio_features_router




app = FastAPI(
    title="Vibely API",
    description="Backend API for Vibely",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(search_router)
app.include_router(audio_features_router)


@app.get("/")
def root():
    return {"message": "Welcome to Vibely!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
