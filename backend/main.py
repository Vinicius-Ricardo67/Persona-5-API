from fastapi import FastAPI, HTTPException
from scraper import scrape_persona_basic

app = FastAPI(
    title="Persona 5 API",
    description="API não oficial de personas do Persona 5",
    version="1.0"
)


@app.get("/")
def home():
    return {"status": "API Persona 5 online"}


@app.get("/persona/basic/{persona_name}")
async def get_persona_basic(persona_name: str):
    try:
        return await scrape_persona_basic(persona_name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
