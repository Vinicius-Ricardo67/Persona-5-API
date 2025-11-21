from fastapi import FastAPI
from routers import personas

app = FastAPI(
    title="PersonaAPI",
    description="Uma API de Persona 5 Royal",
    version="1.0"
)

app.include_router(personas.router)

app.get("/")
def root():
    return {"message": "Bem vindo à PersonaAPI! Acesse /docs para ver a documentação"}