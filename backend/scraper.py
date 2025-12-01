import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
import asyncio

BASE_URL = "https://megamitensei.fandom.com"
API_URL = f"{BASE_URL}/api.php"

MAX_CONCURRENCY = 6
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

async def _api_parse(page_name: str):
    params = {
        "action": "parse",
        "page": page_name,
        "format": "json"
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(API_URL, params=params)

            if r.status_code == 200:
                data = r.json()
                return data["parse"]["text"]["*"]

            print(f"Tentativa {attempt+1}: {r.status_code} para {page_name}")

        except Exception as e:
            print("Erro tentativa", attempt+1, ":", e)

        await asyncio.sleep(1.2 * (attempt+1))

    raise HTTPException(status_code=502, detail=f"Erro ao acessar API para {page_name}")

# Lista dos personas

async def scrape_persona_list():
    html = await _api_parse("List_of_Persona_5_Personas")
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", {"class": "wikitable"})
    if not table:
        raise HTTPException(status_code=500, detail="Tabela de Personas não encontrada")

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
        page_name = href.replace("/wiki/", "") if href else None

        personas.append({
            "id": id_counter,
            "name": name,
            "arcana": arcana,
            "level": level,
            "page": page_name
        })

        id_counter += 1

    return personas

# Página de uma persona

async def scrape_persona_page(page_name: str):
    async with SEMAPHORE:
        html = await _api_parse(page_name)

    soup = BeautifulSoup(html, "html.parser")
    data = {}

    h1 = soup.find("h1")
    data["name"] = h1.get_text(strip=True) if h1 else page_name

    infobox = soup.find("aside")
    if infobox:
        for item in infobox.select("div.pi-item"):
            label = item.find("h3")
            value_el = item.find("div", {"class": "pi-data-value"})

            if not label or not value_el:
                continue

            key = label.get_text(strip=True).lower()
            value = value_el.get_text(" ", strip=True)

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
        headers = [h.get_text(strip=True).lower() for h in table.find_all("th")]
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
        txt = p.get_text(strip=True)
        if txt:
            data["description"] = txt
            break

    return data
