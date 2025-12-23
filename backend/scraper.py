import httpx
import unicodedata
from bs4 import BeautifulSoup

BASE_URL = "https://megamitensei.fandom.com"
API_URL = f"{BASE_URL}/api.php"

SPECIAL_PERSONA_NAMES = {
    "arsene": "Arsène",
    "arsène": "Arsène"
}

PREFERRED_KEYWORDS = [
    "persona 5",
    "persona_5",
    "p5",
    "royal",
    "p5r",
    "persona"
]

HARD_BLACKLIST = [
    "dds",
    "devil",
    "anime"
]

SOFT_BLACKLIST = [
    "smt",
    "megami tensei",
    "mt"
]

def normalize_persona_name(name: str) -> str:
    clean = name.strip().lower()

    if clean in SPECIAL_PERSONA_NAMES:
        return SPECIAL_PERSONA_NAMES[clean]
    
    no_accent = unicodedata.normalize("NFD", clean)
    no_accent = "".join(c for c in no_accent if unicodedata.category(c) != "Mn")

    return no_accent.title().replace(" ", "_")

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

def pick_best_image(infobox):
    images = infobox.find_all("img")
    scored = []

    for img in images:
        src = img.get("src", "")
        if src.startswith("static"):
            src = "https://" + src
        alt = img.get("alt", "").lower()
        name = img.get("data-image-name", "").lower()

        text = f"{src} {alt} {name}".lower()
        score = 0

        for kw in PREFERRED_KEYWORDS:
            if kw in text:
                score += 10

        blocked = False
        for bad in HARD_BLACKLIST:
            if bad in text:
                blocked = True
                break
        if blocked:
            continue

        for bad in SOFT_BLACKLIST:
            if bad in text:
                score -= 5

        if score >= 10:
            scored.append((score, src))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


async def scrape_persona_basic(persona_name: str):
    persona_name = normalize_persona_name(persona_name)

    pages = [
        f"{persona_name}_(Persona_5)",
        persona_name
    ]

    data = None

    for page in pages:
        try:
            data = await _api_parse(page)
            break
        except:
            continue

    if not data:
        raise Exception("Persona não encotrada!")
    
    soup = BeautifulSoup(data["parse"]["text"]["*"], "html.parser")
    name = data["parse"]["title"]

    image = None
    infobox = soup.find("aside", class_="portable-infobox")

    if infobox:
        image = pick_best_image(infobox)

    return {
        "name": name,
        "image": image,
        "source": data["parse"]["title"]
    }