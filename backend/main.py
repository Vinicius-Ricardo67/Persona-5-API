from fastapi import FastAPI
from personas import router as personas_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Persona 5 Scraper API",
    version="1.0.0",
    description="API que faz scrape do Persona 5 Royal Wiki"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(personas_router)

@app.get("/")
def root():
    return {
        "message": "API Persona 5 Online",
        "routes": [
            "/api/v1/personas",
            "/api/v1/personas/{nome}",
            "/api/v1/personas/cache",
            "/api/v1/personas/cache/{nome}"
        ]
    }