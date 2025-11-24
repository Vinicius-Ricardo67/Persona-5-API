from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from cachetools import TTLCache
from typing import Optional
import httpx
from bs4 import BeautifulSoup
import asyncio
import time

router = APIRouter(prefix="/api/v1/personas", tags=["Personas"])

BASE_URL = "https://shinigamitensei.fandom.com"
LIST_URL = f"{BASE_URL}/wiki/List_of_Persona_5_Royal_Personas"

list_cache = TTLCache(maxsize=1, ttl=3600)
persona_cache = TTLCache(maxsize=1000, ttl=600)

MAX_CONCURRENCY = 6
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

CLIENT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Connection": "keep-alive",
}

_preload_status = {"running": False, "started_at": None, "finished_at": None, "processed": 0, "total": 0}

async def _aget(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """GET async com retry e tolerância a erros."""
    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        await asyncio.sleep(1.5 * (attempt + 1))
    return None

# Lista dos personas

async def fetch_persona_list() -> list:
    if "personas_list" in list_cache:
        return list_cache["personas_list"]

    async with httpx.AsyncClient(
        headers=CLIENT_HEADERS,
        http2=True,
        timeout=httpx.Timeout(20, read=25),
        follow_redirects=True
    ) as client:

        text = await _aget(LIST_URL, client)
        if not text:
            raise HTTPException(status_code=502, detail="Erro ao buscar a wiki (lista)")

    soup = BeautifulSoup(text, "html.parser")
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

# Página de uma persona

async def scrape_persona_page(url: str) -> dict:
    if url in persona_cache:
        return persona_cache[url]

    async with SEMAPHORE:
        async with httpx.AsyncClient(
            headers=CLIENT_HEADERS,
            http2=True,
            timeout=httpx.Timeout(20, read=25),
            follow_redirects=True
        ) as client:

            text = await _aget(url, client)
            if not text:
                raise HTTPException(status_code=502, detail=f"Erro ao buscar a página {url}")

    soup = BeautifulSoup(text, "html.parser")
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
                        "level_learned": cols[1].get_text(strip=True),
                    })
            break
    if skills:
        data["skills"] = skills

    for p in soup.find_all("p"):
        txt = p.get_text(strip=True)
        if txt:
            data["description"] = txt
            break

    persona_cache[url] = data
    return data

# Endpoints

@router.get("/")
async def get_personas(
    arcana: Optional[str] = Query(None),
    min_level: Optional[int] = Query(None),
    max_level: Optional[int] = Query(None),
    name: Optional[str] = Query(None),
    limit: Optional[int] = Query(0)
):
    personas = await fetch_persona_list()

    if arcana:
        personas = [p for p in personas if p["arcana"].lower() == arcana.lower()]
    if min_level is not None:
        personas = [p for p in personas if p["level"].isdigit() and int(p["level"]) >= min_level]
    if max_level is not None:
        personas = [p for p in personas if p["level"].isdigit() and int(p["level"]) <= max_level]
    if name:
        personas = [p for p in personas if name.lower() in p["name"].lower()]

    if limit and limit > 0:
        personas = personas[:limit]

    return {"count": len(personas), "results": personas}


@router.get("/{persona_name}")
async def get_persona(persona_name: str):
    personas = await fetch_persona_list()

    matched = next((p for p in personas if p["name"].lower() == persona_name.lower()), None)
    if not matched:
        matched = next((p for p in personas if persona_name.lower() in p["name"].lower()), None)
    if not matched:
        raise HTTPException(status_code=404, detail="Persona not found")

    return await scrape_persona_page(matched["url"])

async def _preload_all_personas():
    global _preload_status

    _preload_status.update(
        {"running": True, "started_at": time.time(), "finished_at": None, "processed": 0}
    )

    personas = await fetch_persona_list()
    urls = [p["url"] for p in personas if p["url"]]
    _preload_status["total"] = len(urls)

    async with httpx.AsyncClient(headers=CLIENT_HEADERS) as client:

        async def job(url):
            try:
                await scrape_persona_page(url)
            except:
                pass
            _preload_status["processed"] += 1

        tasks = [asyncio.create_task(job(u)) for u in urls]
        await asyncio.gather(*tasks)

    _preload_status.update({"running": False, "finished_at": time.time()})


@router.post("/preload")
def start_preload(background_tasks: BackgroundTasks):
    if _preload_status["running"]:
        return {"message": "Preload já está em execução", "status": _preload_status}

    background_tasks.add_task(lambda: asyncio.run(_preload_all_personas()))
    return {"message": "Preload iniciado", "status": _preload_status}


@router.get("/preload/status")
def preload_status():
    return _preload_status

# Cache

@router.delete("/cache")
def clear_all_cache():
    persona_cache.clear()
    list_cache.clear()
    return {"message": "Cache limpo"}