# HealthInsight

Painel analítico sobre dados do SUS (DATASUS/SIH-SUS + CNES), com Oracle
Autonomous Database e Oracle Select AI. Ver `docs/superpowers/specs/` para
o desenho da solução.

## Rodando localmente

1. `python -m venv .venv && source .venv/bin/activate` (ou `.venv\Scripts\activate` no Windows)
2. `pip install -r requirements.txt`
3. Copiar `.env.example` para `.env` e preencher com as credenciais do banco.
4. `uvicorn api.main:app --reload`
