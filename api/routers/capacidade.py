from fastapi import APIRouter, Depends

from api.db import get_connection
from api.queries import capacidade as q

router = APIRouter(prefix="/api", tags=["capacidade"])


@router.get("/ocupacao-estados")
def ocupacao_estados(ano: int = 2026, conn=Depends(get_connection)):
    return q.get_ocupacao_estados(conn, ano)


@router.get("/hospitais")
def hospitais(
    ano: int = 2026,
    regiao: str | None = None,
    tipo: str | None = None,
    conn=Depends(get_connection),
):
    return q.get_hospitais(conn, ano, regiao, tipo)
