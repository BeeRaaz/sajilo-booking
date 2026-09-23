from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Sajilo Booking API!"}
