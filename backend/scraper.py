import httpx
import asyncio
from bs4 import BeautifulSoup
from fastapi import HTTPException

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
            print(f"Erro tentativa {attempt+1}:", e)

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
            "level": int(level) if level.isdigit() else level,
            "page": page
        })

        id_counter += 1

    return personas

def _to_int(x):
    try:
        return int(x)
    except:
        return 0

# Página de uma persona

async def scrape_persona_page(page_name: str):
    async with SEMAPHORE:
        html = await _api_parse(page_name)

    soup = BeautifulSoup(html, "html.parser")
    

    persona = {
        "id": 0,
        "name": None,
        "arcana": None,
        "level": 0,
        "description": None,
        "image": None,
        "strength": 0,
        "magic": 0,
        "endurance": 0,
        "agility": 0,
        "luck": 0,
        "weak": [],
        "resists": [],
        "reflects": [],
        "absorbs": [],
        "nullifies": [],
        "dlc": 0,
        "query": page_name.lower()
    }

    h1 = soup.find("h1")
    if h1:
        persona["name"] = h1.get_text(strip=True)

    infobox = soup.find("aside")
    if infobox:
        
        img = infobox.find("img")
        if img:
            persona["image"] = img.get("src")

        for item in infobox.select("div.pi-item"):
            label = item.find("h3")
            value_el = item.find("div", {"class": "pi-data-value"})
            if not label or not value_el:
                continue

            key = label.get_text(strip=True).lower()
            value = value_el.get_text(" ", strip=True)

            if "arcana" in key:
                persona["arcana"] = value

            elif "level" in key:
                persona["level"] = _to_int(value)

    stats_table = soup.find("table", {"class": "elementtable"})
    if aff_table:
        headers = [h.get_text(strip=True).lower() for h in aff_table.find_all("th")]
        cells = aff_table.find_all("tr")[1].find_all("td")

        for h, c in zip(headers, cell):
            val = c.get_text(strip=True)
            if not val:
                continue

            if "weak" in h:
                persona["weak"].append(val)
            elif "resist" in h:
                persona["resists"].append(val)
            elif "reflect" in h:
                persona["reflects"].append(val)
            elif "absorb" in h:
                persona["absorbs"].append(val)
            elif "null" in h:
                persona["nullifies"].append(val)

    for p in soup,find_all("p"):
        txt = p.get_text(strip=True)
        if txt and len(txt) > 40:
            persona["description"] = txt
            break

    if "↓" in persona["name"]:
        persona["dlc"] = 1

    return persona