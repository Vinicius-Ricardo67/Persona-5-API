import httpx
import asyncio

URL = "https://megamitensei.fandom.com/api.php"

async def test():
    params = {
        "action": "parse",
        "page": "List_of_Persona_5_Personas",
        "format": "json"
    }

    async with httpx.AsyncClient() as c:
        r = await c.get(URL, params=params)
        print("Status:", r.status_code)
        data = r.json()
        html = data["parse"]["text"]["*"]
        print(html[:2000])

asyncio.run(test())