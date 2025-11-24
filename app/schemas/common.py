# app/schemas/common.py
from typing import Any, Annotated
from bson import ObjectId
from pydantic import BaseModel, Field, BeforeValidator, PlainSerializer, WithJsonSchema

def _coerce_object_id(v: Any) -> str:
    """
    Aceita ObjectId do Mongo ou string; devolve SEMPRE string 24-hex.
    """
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")

# Para o Pydantic/Swagger, o tipo é string (com regex), mas validamos/normalizamos.
PyObjectId = Annotated[
    str,
    BeforeValidator(_coerce_object_id),
    PlainSerializer(lambda v: v, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "pattern": "^[a-f0-9]{24}$"})
]

class MongoModel(BaseModel):
    # Alias "_id" do Mongo; nas respostas sai como "id" (string 24-hex)
    id: PyObjectId | None = Field(default=None, alias="_id")

    model_config = {
        "populate_by_name": True,
        # manter aceitação de tipos arbitrários caso apareça algo fora do padrão
        "arbitrary_types_allowed": True,
    }
