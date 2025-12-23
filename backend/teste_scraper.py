import asyncio
from scraper import scrape_persona_basic


async def main():
    persona = input("Digite o nome da Persona: ")

    try:
        result = await scrape_persona_basic(persona)

        print("\nResultado:")
        print("Nome:", result["name"])
        print("Imagem:", result["image"])

    except Exception:
        print("Persona não encontrada.")


asyncio.run(main())