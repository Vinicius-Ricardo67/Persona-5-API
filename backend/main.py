from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from personas import router as personas_router

app = FastAPI(
    title="PersonaAPI (async scraper)",
    version="1.0.0",
    description="API que faz scraping do Persona 5 wiki (async, cache, preload)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(personas_router)

@app.get("/")
def root():
    return {"message": "PersonaAPI (async) - use /api/v1/personas"}