from fastapi import FastAPI, HTTPException
from scraper import (
    scrape_persona_list,
    scrape_persona_page
)


app = FastAPI(
    title="persona 5 api",
    description="API não oficial de personas do Persona 5",
    version="1.0"
)

@app.get("/")
def home():
    return{"status": "API Persona 5 online"}

@app.get("/personas")
async def listar_personas ():
    return await scrape_persona_list()

@app.get("/persona/{page_name}")
async def get_persona(page_name: str):
    return await scrape_persona_page(page_name)