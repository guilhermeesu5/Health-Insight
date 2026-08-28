from fastapi import APIRouter, Depends

from api.db import get_connection
from api.queries import visao_geral as q

router = APIRouter(prefix="/api", tags=["visao-geral"])


@router.get("/kpis")
def kpis(ano: int = 2024, conn=Depends(get_connection)):
    return q.get_kpis(conn, ano)


@router.get("/tendencia-mensal")
def tendencia_mensal(ano: int = 2024, conn=Depends(get_connection)):
    return q.get_tendencia_mensal(conn, ano)


@router.get("/leitos-regiao")
def leitos_regiao(ano: int = 2024, conn=Depends(get_connection)):
    return q.get_leitos_regiao(conn, ano)
