from fastapi import FastAPI

app = FastAPI(
    title="Vibely API",
    description="Backend API for Vibely",
    version="1.0.0"
)


@app.get("/")
def root():
    return {"message": "Welcome to Vibely!"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}