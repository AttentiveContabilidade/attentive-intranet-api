# app/utils/ids.py
from bson import ObjectId
from fastapi import HTTPException, status

def to_oid(id_str: str) -> ObjectId:
    """
    Converte uma string para ObjectId do MongoDB.
    Lança 400 se o formato for inválido.
    """
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID inválido."
        )
