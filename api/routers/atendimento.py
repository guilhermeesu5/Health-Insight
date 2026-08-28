from fastapi import APIRouter, Depends

from api.db import get_connection
from api.queries import atendimento as q

router = APIRouter(prefix="/api", tags=["atendimento"])


@router.get("/tipos-atendimento")
def tipos_atendimento(ano: int = 2024, conn=Depends(get_connection)):
    return q.get_tipos_atendimento(conn, ano)
