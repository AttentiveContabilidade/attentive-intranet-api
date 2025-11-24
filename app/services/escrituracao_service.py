import os
from typing import List, Optional, Dict, Any
from pymongo import MongoClient, ASCENDING
from bson import ObjectId
from app.schemas.escrituracao import (
    EscrituracaoCreate,
    EscrituracaoUpdate,
    EscrituracaoRead,
    EscrituracaoCreateBulk,
    EscrituracaoBulkResult,
)

# Conexão
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB  = os.getenv("MONGO_DB", "Attentive")

_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB]
_collection = _db["escrituracao"]

# Índices recomendados
_collection.create_index([("cnpj", ASCENDING)], unique=True, name="uniq_cnpj")
_collection.create_index([("cod_empresa", ASCENDING)], name="idx_cod_empresa")

def _to_read(doc: Dict[str, Any]) -> EscrituracaoRead:
    """Converte documento do Mongo para schema de resposta (sem senha)."""
    return EscrituracaoRead(
        id=str(doc["_id"]),
        cod_empresa=doc.get("cod_empresa"),
        nome_razao_social=doc["nome_razao_social"],
        cnpj=doc["cnpj"],
        login=doc.get("login"),
    )

def create(payload: EscrituracaoCreate) -> EscrituracaoRead:
    data = payload.model_dump()
    # nunca gravar None em campos opcionais à toa
    data = {k: v for k, v in data.items() if v is not None}
    inserted = _collection.insert_one(data)
    doc = _collection.find_one({"_id": inserted.inserted_id})
    return _to_read(doc)

def get_by_id(id_str: str) -> Optional[EscrituracaoRead]:
    try:
        oid = ObjectId(id_str)
    except Exception:
        return None
    doc = _collection.find_one({"_id": oid})
    return _to_read(doc) if doc else None

def get_by_cnpj(cnpj: str) -> Optional[EscrituracaoRead]:
    doc = _collection.find_one({"cnpj": cnpj})
    return _to_read(doc) if doc else None

def list_many(skip: int = 0, limit: int = 50) -> List[EscrituracaoRead]:
    cursor = _collection.find({}, {"senha": 0}).skip(skip).limit(limit).sort("nome_razao_social", ASCENDING)
    return [_to_read(d) for d in cursor]

def update(id_str: str, payload: EscrituracaoUpdate) -> Optional[EscrituracaoRead]:
    try:
        oid = ObjectId(id_str)
    except Exception:
        return None
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        doc = _collection.find_one({"_id": oid})
        return _to_read(doc) if doc else None

    _collection.update_one({"_id": oid}, {"$set": updates})
    doc = _collection.find_one({"_id": oid})
    return _to_read(doc) if doc else None

def delete(id_str: str) -> bool:
    try:
        oid = ObjectId(id_str)
    except Exception:
        return False
    res = _collection.delete_one({"_id": oid})
    return res.deleted_count == 1

def create_bulk(payload: EscrituracaoCreateBulk) -> EscrituracaoBulkResult:
    # Normaliza e prepara os docs
    docs: List[Dict[str, Any]] = []
    cnpjs: List[str] = []
    for item in payload.items:
        d = item.model_dump(exclude_none=True)
        docs.append(d)
        cnpjs.append(d["cnpj"])

    skipped: List[str] = []
    inserted_ids: List[str] = []
    errors: List[str] = []

    # Se optar por ignorar duplicados, filtramos antes
    to_insert = docs
    if payload.skip_duplicates:
        already = set(
            x["cnpj"] for x in _collection.find({"cnpj": {"$in": cnpjs}}, {"cnpj": 1, "_id": 0})
        )
        skipped = sorted(list(already))
        to_insert = [d for d in docs if d["cnpj"] not in already]

    if not to_insert:
        return EscrituracaoBulkResult(
            inserted=0, inserted_ids=[], skipped=skipped, errors=[]
        )

    try:
        res = _collection.insert_many(to_insert, ordered=False)
        inserted_ids = [str(_id) for _id in res.inserted_ids]
    except Exception as e:
        # Se não usar skip_duplicates, podemos cair aqui por duplicidade (11000)
        # Tenta identificar duplicados no erro
        msg = str(e)
        errors.append(msg)

        # coleta o que entrou (quando possível)
        try:
            inserted_ids = [str(_id) for _id in e.details.get("insertedIds", []) if _id]
        except Exception:
            pass

    return EscrituracaoBulkResult(
        inserted=len(inserted_ids),
        inserted_ids=inserted_ids,
        skipped=skipped,
        errors=errors,
    )