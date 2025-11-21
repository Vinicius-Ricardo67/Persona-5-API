from fastapi import APIRouter, HTTPException, Query
from cachetools import TTLCache
from typing import Optional
import requests
from bs4 import BeautifulSoup

router = APIRouter(prefix="/api/v1/personas", tags=["Personas"])

BASE_URL = "https://shinigamitensei.fandom.com"
LIST_URL = f"{BASE_URL}/wiki/List_of_Persona_5_Royal_Personas"

list_cache = TTLCache(maxsize=1, ttl=3600)
persona_cache = TTLCache(maxsize=200, ttl=600)

session = requests.Session()
session.headers.update({
    "User-Agent": "PersonaAPI-scraper/1.0 (contact: your@email)"
})

# Lista principal dos personas

def fetch_persona_list():
    """
    Faz scrape da tabela principal da wiki e retorna uma lista contendo:
    {id, name, arcana, level, url}

    Usa cache (list_cache) por 1 hora.
    """
    if "personas_list" in list_cache:
        return list_cache["personas_list"]

    resp = session.get(LIST_URL, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Erro ao buscar a wiki (lista)")

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "wikitable"})
    if not table:
        raise HTTPException(status_code=500, detail="Tabela de personas não encontrada")

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

# Scraper

def scrape_persona_page(url: str):
    """
    Faz scrape dos dados detalhados de uma página individual.
    Retorna dict com:
    - name
    - arcana
    - level
    - inherits
    - item / item held
    - stats
    - skills
    - description
    - image_url

    Usa cache (persona_cache) por 10 minutos.
    """

    if url in persona_cache:
        return persona_cache[url]

    resp = session.get(url, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar a página {url}")

    soup = BeautifulSoup(resp.text, "html.parser")
    data = {}

    heading = soup.find("h1", {"id": "firstHeading"})
    data["name"] = heading.get_text(strip=True) if heading else None

    infobox = soup.find("aside", {"role": "region"})
    if infobox:
        for item in infobox.select("div.pi-item"):
            label = item.find("h3")
            if not label:
                continue

            key = label.get_text(strip=True).lower()
            value = item.find("div", {"class": "pi-data-value"})
            value_text = value.get_text(" ", strip=True) if value else ""

            if "arcana" in key:
                data["arcana"] = value_text
            elif "level" in key:
                data["level"] = value_text
            elif "inherits" in key:
                data["inherits"] = value_text
            elif "item" in key or "held" in key:
                data["item"] = value_text

        img = infobox.find("img")
        if img and img.get("src"):
            data["image_url"] = img["src"]

    stats_table = soup.find("table", {"class": "wikitable"})
    if stats_table:
        headers = [th.get_text(strip=True).lower() for th in stats_table.find_all("th")]
        rows = stats_table.find_all("tr")[1:]

        if rows:
            stat_values = [td.get_text(strip=True) for td in rows[0].find_all("td")]
            if len(stat_values) == len(headers):
                data["stats"] = dict(zip(headers, stat_values))

    skills = []
    for table in soup.find_all("table", {"class": "wikitable"}):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if any("skill" in h for h in headers):
            for r in table.find_all("tr")[1:]:
                cols = r.find_all("td")
                if len(cols) >= 2:
                    skills.append({
                        "name": cols[0].get_text(strip=True),
                        "level_learned": cols[1].get_text(strip=True)
                    })
            break

    if skills:
        data["skills"] = skills

    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            data["description"] = text
            break

    persona_cache[url] = data
    return data

# Endpoint para as listas

@router.get("/")
def get_personas(
    arcana: Optional[str] = Query(None, description="Filtra por arcana"),
    min_level: Optional[int] = Query(None, description="Nível mínimo"),
    max_level: Optional[int] = Query(None, description="Nível máximo"),
    name: Optional[str] = Query(None, description="Busca por nome"),
    limit: Optional[int] = Query(0, description="Limite (0 = sem limite)")
):
    """
    Retorna a lista de personas com filtros opcionais.
    """
    personas = fetch_persona_list()

    if arcana:
        personas = [p for p in personas if p["arcana"].lower() == arcana.lower()]
    if min_level is not None:
        personas = [p for p in personas if p["level"].isdigit() and int(p["level"]) >= min_level]
    if max_level is not None:
        personas = [p for p in personas if p["level"].isdigit() and int(p["level"]) <= max_level]
    if name:
        personas = [p for p in personas if name.lower() in p["name"].lower()]

    if limit > 0:
        personas = personas[:limit]

    return {"count": len(personas), "results": personas}

@router.get("/{persona_name}")
def get_persona(persona_name: str):
    """
    Busca uma persona pelo nome ou parte do nome.
    Retorna todos os dados completos da página individual.
    Usa cache de 10 minutos.
    """
    personas = fetch_persona_list()

    matched = next(
        (p for p in personas if p["name"].lower() == persona_name.lower()),
        None
    )

    if not matched:
        matched = next(
            (p for p in personas if persona_name.lower() in p["name"].lower()),
            None
        )

    if not matched:
        raise HTTPException(status_code=404, detail="Persona não encontrada")

    if not matched["url"]:
        raise HTTPException(status_code=500, detail="URL não encontrada")

    return scrape_persona_page(matched["url"])

# Endpoints do cache

@router.delete("/cache/{persona_name}")
def clear_persona_cache(persona_name: str):
    """
    Limpa apenas o cache de uma persona específica.
    """
    personas = list_cache.get("personas_list")

    if personas:
        for p in personas:
            if p["name"].lower() == persona_name.lower():
                url = p.get("url")
                if url and url in persona_cache:
                    del persona_cache[url]
                    return {"message": f"Cache de {persona_name} limpo"}

    return {"message": f"{persona_name} não estava em cache"}


@router.delete("/cache")
def clear_all_cache():
    """
    Limpa TODO o cache da API (lista + personas individuais)
    """
    persona_cache.clear()
    list_cache.clear()
    return {"message": "Cache geral limpo"}
