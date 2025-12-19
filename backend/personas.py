import asyncio
from scraper import scrape_persona_page

async def test():
    p = await scrape_persona_page("Jack_Frost")
    print(p)

asyncio.run(test())