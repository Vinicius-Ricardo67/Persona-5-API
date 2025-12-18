import httpx
import asyncio
from bs4 import BeautifulSoup
from fastapi import HTTPException

BASE_URL = "https://megamitensei.fandom.com"
API_URL = f"{BASE_URL}/api.php"

MAX_COURRENCY = 6
SEMAPHORE = asyncio.Semaphore(MAX_COURRENCY)

async def _api_parse(page_name: str):
    params = {
        "action": "parse",
        "page": page_name,
        "format": "json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(API_URL, params=params)
    
    if r.status_code == 200:
        data = r.json()
        return data["parse"]["text"]["*"]

    raise HTTPException(status_code=404, detail=f"Página não encontrada: {page_name}")

def _to_int(x):
    try:
        return int(x)
    except:
        return 0

async def scrape_persona_page(page_name: str):

    original = page_name
    tried = []

    p5_page = f"{original}_(Persona_5)"
    tried.append(p5_page)

    try:
        html = await _api_parse(p5_page)
        fallback_mode = 0
    
    except:
        p5r_page = f"{original}_(Persona_5_Royal)"
        tried.append(p5r_page)
        try:
            html = await _api_parse(p5r_page)
            fallback_mode = 0
        except:
            tried.append(original)
            html = await _api_parse(original)
            fallback_mode = 2

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
        "reflect": [],
        "absorbs": [],
        "nullifies": [],
        "dlc": fallback_mode,
        "query": page_name.lower()
    }

    h1 = soup.find("h1")
    if h1:
        persona["name"] = h1.get_text(strip=True)

    infobox = soup.find("aside", {"class": "portable-infobox"})
    if infobox:
        img = infobox.find("img")
        if img:
            persona["image"] = img.get("src")

        for item in infobox.select(".pi-item.pi-data"):
            label = item.find(class_="pi-data-label")
            value_el = item.find(class_="pi-data-value")

            if not label or not value_el:
                continue

            key = label.get_text(strip=True).lower()
            value = value_el.get_text(" ", strip=True)

            if "arcana" in key:
                persona["arcana"] = value
            elif "level" in key:
                persona["level"] = _to_int(value)

    possible_tables = ["attributetable", "elementtable", "wikitable"]
    stats_table = None

    for cls in possible_tables:
        t = soup.find("table", {"class": cls})
        if t:
            stats_table = t
            break
    
    if stats_table:
        rows = stats_table.find_all("tr")
        if len(rows) >= 2:
            headers: [h.get_text(strip=True).lower() for h in rows[0].find_all("th")]
            values = [c.get_text(strip=True) for c in rows[1].find_all("td")]

            for h, v in zip(headers, values):
                val = _to_int(v)

                if "strength" in h:
                    persona["strength"] = val
                elif "magic" in h:
                    persona["magic"] = val
                elif "endurance" in h or "end" in h:
                    persona["endurance"] = val
                elif "agility" in h:
                    persona["agility"] = val
                elif "luck" in h:
                    persona["luck"] = val

    aff_table = soup.find("table", {"class": "elementtable"})
    if aff_table:
        rows = aff_table.find_all("tr")

        if len(rows) >= 2:
            headers = [h.get_text(strip=True).lower() for h in rows[0].find_all("th")]
            cells = rows[1].find_all("td")

        for h, c in zip(headers, cells):
            val = c.get_text(strip=True)

            if "weak" in h:
                persona["weak"].append(val)
            elif "resist" in h:
                persona["resists"].append(val)
            elif "null" in h:
                persona["nullifies"].append(val)
            elif "absorb" in h:
                persona["absorbs"].append(val)
            elif "reflect" in h:
                persona["reflects"].append(val)
            
    for p in soup.find_all("p"):
        txt = p.get_text(strip=True)
        if txt and len(txt) > 40:
            persona["description"] = txt
            break

    return persona