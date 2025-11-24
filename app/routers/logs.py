# app/routers/logs.py
from typing import Any, Dict, List
from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException
from fastapi.encoders import jsonable_encoder

# Compat: tenta importar do módulo novo (mongodb) e cai para o antigo (mongo)
try:
    from app.db.mongodb import get_db_logs  # type: ignore
except Exception:
    from app.db.mongo import get_db_logs  # type: ignore

router = APIRouter(tags=["logs"])

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@router.post("/logs", summary="Inserir um log (flexível, sem schema rígido)")
async def create_log(
    payload: Dict[str, Any] = Body(
        ...,
        example={"source": "crawler", "action": "run_start", "ok": True, "meta": {"run_id": "abc"}}
    )
):
    """
    Recebe um dicionário **livre** e insere na coleção `logs`.
    O servidor adiciona automaticamente `ts` (timestamp UTC ISO8601).
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload deve ser um objeto JSON (dict).")

    db_logs = await get_db_logs()
    doc = {"ts": _now_iso(), **payload}
    res = await db_logs["logs"].insert_one(jsonable_encoder(doc))
    return {"inserted_id": str(res.inserted_id)}

@router.post(
    "/logs/bulk",
    summary="Inserir vários logs de uma vez (bulk, flexível)",
    description="Aceita uma **lista** de objetos livres. Cada item recebe `ts` automaticamente."
)
async def create_logs_bulk(
    items: List[Dict[str, Any]] = Body(
        ...,
        example=[
            {"source": "crawler", "action": "run_start", "ok": True, "meta": {"run_id": "abc"}},
            {"source": "crawler", "action": "event", "ok": False, "meta": {"run_id": "abc", "err": "timeout"}}
        ]
    )
):
    if not isinstance(items, list) or any(not isinstance(it, dict) for it in items):
        raise HTTPException(status_code=400, detail="Body deve ser uma lista de objetos JSON.")

    if len(items) == 0:
        return {"inserted_count": 0, "inserted_ids": []}

    docs = [{"ts": _now_iso(), **it} for it in items]
    db_logs = await get_db_logs()
    res = await db_logs["logs"].insert_many(jsonable_encoder(docs))
    return {
        "inserted_count": len(res.inserted_ids),
        "inserted_ids": [str(_id) for _id in res.inserted_ids],
    }

@router.get("/logs/recent", summary="Listar logs recentes")
async def recent_logs(limit: int = 5):
    db_logs = await get_db_logs()
    cur = db_logs["logs"].find().sort("_id", -1).limit(int(limit))
    out = []
    for it in await cur.to_list(length=int(limit)):
        it["_id"] = str(it.get("_id"))
        out.append(it)
    return out
