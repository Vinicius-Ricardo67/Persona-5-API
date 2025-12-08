import httpx
import asyncio
from bs4 import BeautifulSoup

URL = "https://megamitensei.fandom.com/api.php?action=parse&page=List_of_Persona_5_Personas&format=json"

async def test():
    async with httpx.AsyncClient() as c:
        r = await c.get(URL)
        print("Status:", r.status_code)

        data = r.json()
        html = data["parse"]["text"]["*"]

        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")
        if table:
            print("Tabela encontrada!")
            print(str(table)[:2000])
        else:
            print("Nenhuma tabela encontrada")

asyncio.run(test()) 