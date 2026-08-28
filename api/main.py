from fastapi import FastAPI

from api.routers import visao_geral, capacidade

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)
app.include_router(capacidade.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
