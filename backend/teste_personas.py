import asyncio
from scraper import scrape_persona_page

async def main():
    page = input("Nome da persona na wiki: ").strip()
    page = page.replace(" ", "_")
    data = await scrape_persona_page(page)
    print(data)

asyncio.run(main())