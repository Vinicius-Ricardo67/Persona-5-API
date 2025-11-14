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

def scrape_persona_pages(url: str):
    """
    Extrai todos os dados detalhados de uma persona pela página individual.
    Retorna o dict com os campos: name, arcana, level, inherits, stats, skills, description e image_url.
    """

    if url in persona_cache:
        return persona_cache[url]

    resp.session.get(url, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar a wiki (page {url})")
    
    soup = BeutifulSoup(resp.text, ("html.parser"))
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
                data ["level"] = value_text
            elif "inherits" in key:
                data ["inherits"] = value_text
            elif "item" in key or "held" in key:
                data ["item"] = value_text
            
        img = infobox.find("img")
        if img and img.get("src"):
            data["image_url"] = img["src"]

    stats_table = soup.find("table", {"class": "wikitable"})
    if stats_table:
        headers = [th.get_text(strip=True).lower() for th in stats_table.find_all("th")]
        rows = stats_table.find_all("tr")[1:]
        if rows:
            stats_vals = [td.get_text(strip=True) for td in rows[0].find_all("td")]
            if len(headers) == len(stats_vals):
                data["stats"] = dict(zip(headers, stats_vals))

    skills = []
    skills_anchor = soup.find(id="Skills")
    if skills_anchor:
        parent - skills_anchor
        table = None
        h2 = skills_anchor.find_parent(["h2", "h3"])
        if h2:
            sibiling = h2.find_next_sibiling()
            while sibiling:
                if sibiling.name == "table":
                    table = sibiling
                    break
                sibiling = sibiling.find_next_sibiling()
        if table:
            for r in table.find_all("tr")[1:]:
                cols = r.find_all(["td", "th"])
                if len(cols) >= 2:
                    name = cols[0].get_text(strip=True)
                    lvl = cols[1].get_text(strip=True)
                    skills.append({"name": name, "level_learned": lvl})
                    
    if not skills:
        for r in soup.find_all("table", {"class": "wikitable"}):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
            if any("skill" in h for h in headers):
                for r in table.find_all("tr")[1:]:
                    cols = r.find_all("td")
                    if len(cols) >= 2:
                        skills.append({
                            "name": cols[0].get_text(strip=True),
                            "level_learned": cols[1].get_text(strip=True)
                        })
                if skills:
                    break
    
    if skills:
        data["skills"] = skills

    paragraphs = soup.find_all("p")
    for p in paragraphs:
        text = p.get_text(strip=True)
        if text:
            data["description"] = text
            break

    persona_cache[url] = data
    return data
@router.get("/")
def get_personas(
    arcana: Optional[str] = Query(None, description="Filtra por arcana"),
    min_level: Optional[int] = Query(None, description="Nível mínimo"),
    max_level: Optional[int] = Query(None, description="Nível máximo"),
    name: Optional[str] = Query(None, description="Busca por nome"),
    limit: Optional[int] = Query(0, description="Limite de resultados (0 = sem limite)")
):
    """
    Retorna lista básica de personas (nome, arcana, level, url).
    Usa cache (1 hora) para a lista inteira.
    Filtros: arcana, min_level, max_level, name, limit.
    """
    personas = fetch_persona_list()

    if arcana:
        personas = [p for p in personas if p.get("arcana") and p["arcana"].lower() == arcana.lower()]
    if min_level is not None:
        personas = [p for p in personas if p.get("level") and p["level"].isdigit() and int(p["level"]) >= min_level]
    if max_level is not None:
        personas = [p for p in personas if p.get("level") and p["level"].isdigit() and int(p["level"]) <= max_level]
    if name:
        personas = [p for p in personas if name.lower() in p.get("name", "").lower()]

    if limit and limit > 0:
        personas = personas[:limit]

    return {"count": len(personas), "results": personas}

