from fastapi import FastAPI

from api.routers import visao_geral, capacidade, atendimento

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)
app.include_router(capacidade.router)
app.include_router(atendimento.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
