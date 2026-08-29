from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.db import get_connection
from api.queries import ai as q

router = APIRouter(prefix="/api/ai", tags=["ai"])


class PerguntaIn(BaseModel):
    pergunta: str = Field(min_length=1)


@router.post("/query")
def query(body: PerguntaIn, conn=Depends(get_connection)):
    return q.perguntar(conn, body.pergunta)
