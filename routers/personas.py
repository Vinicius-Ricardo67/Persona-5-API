from fastapi import APIRouter, HTTPException, Query
from cachetools import TTLCahe
from typing import Optional
import requests
from bs4 import BeutifulSoup
import time

router = APIRouter(prefix="/api/v1/personas", tags=["Personas"])

BASE_URL = "https://shinigamitensei.fandom.com"
LIST_URL = f"{BASE_URL}/wiki/List_of_Persona_5_Royal_Personas"

list_cache = TTLCahe(maxsize=1, ttl=3600)
persona_cache = TTLCahe(maxsize=200, ttl=600)

session = requests.Session()
session.headers.update({
    "User-Agent": "PersonaAPI-scraper/1.0 (contact: your@email)"
})

def fetch_persona_list():
    """
    Busca a tabela principal da wiki e retorna uma lista básica com
    {name, arcana, level, url}.
    Usa o cache (list_cache)
    """
    
    if "persona_list" in list_cache:

        return list_cache["personas_list"]

    resp = session.get(LIST_URL, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Erro ao buscar a wiki (lista)")

    soup = BeutifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "wikitable"})
    if not table:
        raise HTTPException(status_code=500, detail="Tabela de personas não encontrada na wiki")

    rows = table.find_all("tr")[1:]
    personas = []
    id_counter = 1
    for row in rows:
        a = row.find("a")
        cols = row.find_all("td")
        if not a or len(cols) < 3:
            continue
        name = a.get_text(strip=True)
        arcana = cols[1].get_text(strip=True)
        level = cols[2].get_text(strip=True)
        href = a.get("href")
        url = BASE_URL + href if href else None
        personas.append({
            "id": id_counter,
            "name": name,
            "arcana": arcana,
            "level": level,
            "url": url
        })
        id_counter += 1

    list_cache["personas_list"] = personas
    return personas