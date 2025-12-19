import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

BASE_URL = "https://megamitensei.fandom.com"
API_URL = f"{BASE_URL}/api.php"


async def _api_parse(page_name: str):
    params = {
        "action": "parse",
        "page": page_name,
        "format": "json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(API_URL, params=params)

    data = r.json()

    if "parse" not in data:
        raise Exception("Página não encontrada")

    return data


async def scrape_persona_basic(persona_name: str):
    pages = [
        f"{persona_name}_(Persona_5)",
        persona_name
    ]

    data = None
    used_page = None

    for page in pages:
        try:
            data = await _api_parse(page)
            used_page = page
            break
        except:
            continue

    if not data:
        raise HTTPException(status_code=404, detail="Persona não encontrada")

    soup = BeautifulSoup(data["parse"]["text"]["*"], "html.parser")

    name = data["parse"]["title"]

    image = None
    infobox = soup.find("aside", class_="portable-infobox")
    if infobox:
        img = infobox.find("img")
        if img:
            image = img.get("src")

    return {
        "name": name,
        "image": image,
        "source": used_page
    }
