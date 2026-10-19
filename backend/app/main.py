from fastapi import FastAPI
from app.routes.auth import router as auth_router

app = FastAPI(
    title="Vibely API",
    description="Backend API for Vibely",
    version="1.0.0",
)

app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "Welcome to Vibely!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
