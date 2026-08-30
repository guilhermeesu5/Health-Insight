# HealthInsight

Painel analítico sobre dados do SUS (DATASUS/SIH-SUS + CNES), com Oracle
Autonomous Database como core de dados e Oracle Select AI para consultas
em linguagem natural. Projeto do Challenge FIAP/Oracle — Grupo 35.

**Aplicação publicada:** http://64.181.175.100/

> Dados carregados atualmente: 5 UFs (AC, DF, CE, SC, AM), competência
> 2024-01. Ver `docs/arquitetura.md` para detalhes e limitações conhecidas.

## Estrutura do repositório

- `etl/` — `download.py` (download DATASUS/CNES via `pysus`),
  `transform.py` (tratamento/classificação) e `load.py` (carga no Oracle
  Autonomous Database); testes em `etl/tests/`.
- `sql/` — `schema.sql` (DDL das tabelas) e `select_ai_setup.sql`
  (configuração do perfil Oracle Select AI).
- `notebooks/` — `eda_modelo.ipynb`: análise exploratória (EDA) e modelo
  preditivo de internações, com os gráficos gerados (`output_*.png`).
- `api/` — backend FastAPI: `main.py`, `config.py`, `db.py`, endpoints em
  `api/routers/` e consultas SQL em `api/queries/` (visão geral,
  capacidade hospitalar, análise de atendimento, IA); testes em
  `api/tests/`. Também serve o front-end estático
  (`api/static/index.html`).
- `deploy/` — arquivos de configuração do deploy em produção:
  `healthinsight-api.service` (systemd) e `nginx-healthinsight.conf`
  (proxy reverso).
- `docs/` — `arquitetura.md` (este diagrama/descrição da arquitetura
  implementada) e `docs/superpowers/` (spec de design e plano de
  implementação usados durante o desenvolvimento).

## Rodando localmente

1. `python -m venv .venv && .venv\Scripts\activate` (Windows) ou
   `source .venv/bin/activate` (Linux/Mac)
2. `pip install -r requirements.txt`
3. Copiar `.env.example` para `.env` e preencher com as credenciais do
   Oracle Autonomous Database (ver
   `docs/superpowers/plans/2026-08-21-healthinsight-mvp.md`, Task 1).
4. Baixar o wallet de conexão do banco para `./wallet/` (Task 1).
5. Rodar o pipeline de dados uma vez: `python -m etl.load`
6. Subir a API: `uvicorn api.main:app --reload`
7. Abrir `http://localhost:8000/`

## Testes

```bash
pytest etl/tests api/tests -v
```

## Documentação

- Spec de arquitetura: `docs/superpowers/specs/2026-08-21-healthinsight-mvp-design.md`
- Plano de implementação: `docs/superpowers/plans/2026-08-21-healthinsight-mvp.md`
- Arquitetura implementada (fluxo de dados, tecnologias, limitações
  conhecidas): `docs/arquitetura.md`
