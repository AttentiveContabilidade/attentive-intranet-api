# app/startup.py
from app.db.mongo import get_db
from pymongo.errors import OperationFailure
from pymongo import ASCENDING, DESCENDING


async def _safe_create_index(coll, keys, **kwargs):
    """
    Cria índice e ignora conflito de nome (code 85) quando o índice equivalente já existe.
    Mantém o índice existente sem derrubar produção.
    """
    try:
        return await coll.create_index(keys, **kwargs)
    except OperationFailure as e:
        # 85 = IndexOptionsConflict (ex.: já existe "email_1" e você tentou criar "uniq_usuarios_email")
        if e.code == 85:
            return None
        raise


async def ensure_indexes():
    """
    Cria (ou verifica) índices únicos e auxiliares das principais coleções.
    Executa no startup via lifespan em main.py.
    """
    db = await get_db()

    # ======== USUÁRIOS ========
    await _safe_create_index(db["usuarios"], "email", unique=True, name="uniq_usuarios_email")

    # ======== EMPRESAS ========
    await _safe_create_index(db["empresas"], "cnpj", unique=True, name="uniq_empresas_cnpj")

    # ======== DEPARTAMENTOS ========
    await _safe_create_index(db["departamentos"], "slug", unique=True, name="uniq_departamentos_slug")
    await _safe_create_index(db["departamentos"], "parent_id", name="idx_departamentos_parent")
    await _safe_create_index(db["departamentos"], "path", name="idx_departamentos_path")
    # se você adicionou path_slugs no router:
    await _safe_create_index(db["departamentos"], "path_slugs", name="idx_departamentos_path_slugs")
    await _safe_create_index(db["departamentos"], "ativo", name="idx_departamentos_ativo")

    # ======== CURSOS ========
    await _safe_create_index(db["cursos"], "slug", unique=True, name="uniq_cursos_slug")
    await _safe_create_index(db["cursos"], "departamento_slug", name="idx_cursos_departamento")
    await _safe_create_index(db["cursos"], [("ativo", 1), ("nome", 1)], name="idx_cursos_ativos_nome")

    # ======== COMUNICADOS ========
    await _safe_create_index(db["comunicados"], [("status", ASCENDING), ("created_at", DESCENDING)], name="idx_comunicados_status_data")
    await _safe_create_index(db["comunicados"], [("tipo", ASCENDING), ("created_at", DESCENDING)], name="idx_comunicados_tipo_data")
    await _safe_create_index(db["comunicados"], [("autor_id", ASCENDING), ("created_at", DESCENDING)], name="idx_comunicados_autor_data")
    await _safe_create_index(db["comunicados"], [("target_user_id", ASCENDING), ("created_at", DESCENDING)], name="idx_comunicados_target_data")

    print("✅ Índices verificados/criados com sucesso!")
