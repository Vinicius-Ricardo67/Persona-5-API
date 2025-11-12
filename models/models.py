from pydantic import BaseModel
from typing import Dict, List

class Persona(BaseModel):
    id: int
    name: str
    arcana: str
    level: int
    affinities: Dict[str, str]
    skills: List[str]
    image: str