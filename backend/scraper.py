import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
import asyncio

BASE_URL = "https://megamitensei.fandom.com"
LIST_URL = f"{BASE_URL}/wiki/List_of_Persona_5_Personas"

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

MAX_CONCURRENCY = 6
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

async def _aget(url: str, client: httpx.AsyncClient):
    for attempt in range(3):
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text

        except Exception:
            pass

        await asyncio.sleep(1.2 * (attempt + 1))

    return None

async def scrape_persona_list():
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
        cols = row.find_all("td")
        a = row.find("a")

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

    return personas

async def scrape_persona_page(url: str):
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
            value_el = item.find("div", {"class": "pi-data-value"})
            value = value_el.get_text(" ", strip=True) if value_el else ""

            if "arcana" in key:
                data["arcana"] = value
            elif "level" in key:
                data["level"] = value
            elif "inherits" in key:
                data["inherits"] = value
            elif "item" in key:
                data["item"] = value

        img = infobox.find("img")
        if img and img.get("src"):
            data["image_url"] = img["src"]

    stats_table = soup.find("table", {"class": "wikitable"})
    if stats_table:
        headers = [th.get_text(strip=True).lower() for th in stats_table.find_all("th")]
        rows = stats_table.find_all("tr")[1:]
        if rows:
            values = [td.get_text(strip=True) for td in rows[0].find_all("td")]
            if len(values) == len(headers):
                data["stats"] = dict(zip(headers, values))

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

    return data
