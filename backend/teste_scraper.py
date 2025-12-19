import asyncio
from scraper import scrape_persona_basic

async def main():
    persona = input("Digite o nome da Persona: ")
    result = await scrape_persona_basic(persona)

    print("\nResultado: ")
    print("nome: ", result["name"])
    print("Imagem: ", result["image"])

asyncio.run(main()) 