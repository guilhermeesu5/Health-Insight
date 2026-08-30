# HealthInsight MVP Funcional — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o dashboard mockado (`index.html`) em uma aplicação real: dados do DATASUS/CNES carregados em um Oracle Autonomous Database, uma API FastAPI servindo esses dados ao front-end existente, e Oracle Select AI real por trás da tela de perguntas em linguagem natural — tudo publicado com um link acessível hospedado na OCI.

**Architecture:** Um único processo FastAPI serve tanto os arquivos estáticos (`index.html` adaptado) quanto os endpoints JSON usados pelos 4 dashboards, e um endpoint que aciona o Select AI configurado diretamente no banco. Scripts de ETL separados baixam e tratam os dados públicos e os carregam no schema relacional do banco. Um notebook cobre EDA e um modelo preditivo simples. Deploy em uma única Compute Instance OCI (uvicorn atrás de nginx).

**Tech Stack:** Python 3.11, FastAPI, python-oracledb (thin mode), pandas, pysus (download SIH-SUS/CNES), pytest + httpx (testes), Oracle Autonomous Database + Select AI (DBMS_CLOUD_AI), Chart.js (já existente no front-end), nginx + systemd (deploy), OCI Compute Instance.

**Spec:** [docs/superpowers/specs/2026-08-21-healthinsight-mvp-design.md](../specs/2026-08-21-healthinsight-mvp-design.md)

## Global Constraints

- O design visual do `index.html` (CSS, layout, Chart.js) é preservado — só a origem dos dados muda, de arrays fixos para `fetch()`.
- Um único processo/serviço (FastAPI) serve tanto os estáticos quanto a API — sem servidor de frontend separado, sem CORS a configurar.
- Sem autenticação/autorização de usuários — fora de escopo (spec, seção "Fora de escopo").
- Toda a infraestrutura (banco, Select AI, deploy) roda exclusivamente na OCI, na mesma conta.
- Dados devem ser reais, baixados do DATASUS/TabNet (SIH-SUS) e/ou CNES — não sintéticos.
- Profundidade analítica: EDA documentada + um modelo preditivo simples e explicável (spec, "Decisões já tomadas").

---

## Task 0: Scaffolding do repositório

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create (pastas vazias com `.gitkeep` onde necessário): `etl/`, `api/routers/`, `api/queries/`, `api/tests/`, `api/static/`, `notebooks/`, `sql/`

**Interfaces:**
- Produces: estrutura de pastas que todas as tasks seguintes assumem existir; `requirements.txt` com todas as dependências do projeto.

- [ ] **Step 1: Criar a estrutura de pastas**

```bash
mkdir -p etl api/routers api/queries api/tests api/static notebooks sql
```

- [ ] **Step 2: Criar `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
oracledb==2.4.1
pandas==2.2.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
pysus==0.14.1
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 3: Criar `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
wallet/
.ipynb_checkpoints/
*.dbc
*.dbf
data/raw/
```

- [ ] **Step 4: Criar `.env.example`**

```
ORACLE_USER=ADMIN
ORACLE_PASSWORD=troque-me
ORACLE_DSN=healthinsightdb_high
ORACLE_WALLET_DIR=./wallet
```

- [ ] **Step 5: Criar `README.md` (skeleton, será completado na Task 18)**

```markdown
# HealthInsight

Painel analítico sobre dados do SUS (DATASUS/SIH-SUS + CNES), com Oracle
Autonomous Database e Oracle Select AI. Ver `docs/superpowers/specs/` para
o desenho da solução.

## Rodando localmente

1. `python -m venv .venv && source .venv/bin/activate` (ou `.venv\Scripts\activate` no Windows)
2. `pip install -r requirements.txt`
3. Copiar `.env.example` para `.env` e preencher com as credenciais do banco.
4. `uvicorn api.main:app --reload`
```

- [ ] **Step 6: Criar ambiente virtual e instalar dependências**

```bash
python -m venv .venv
```

No Windows (PowerShell):
```bash
.venv\Scripts\pip install -r requirements.txt
```

- [ ] **Step 7: Verificar que as dependências principais importam**

```bash
.venv\Scripts\python -c "import fastapi, oracledb, pandas, pysus; print('ok')"
```

Expected: imprime `ok` sem erro.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .gitignore .env.example README.md etl api notebooks sql
git commit -m "chore: scaffolding do repositorio (pastas, deps, README)"
```

---

## Task 1: Provisionar Oracle Autonomous Database

Task manual (console/CLI OCI) — sem código de aplicação, mas com passos exatos e uma verificação executável ao final.

**Files:**
- Create: `wallet/` (baixado do console OCI, **não commitado** — está no `.gitignore`)

**Interfaces:**
- Produces: instância Autonomous Database ativa, wallet de conexão, credenciais (`ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_DSN`) usadas por todas as tasks de ETL e backend.

- [ ] **Step 1: Criar a instância no console OCI**

No console OCI → Oracle Database → Autonomous Database → Create Autonomous Database:
- Nome: `healthinsightdb`
- Workload type: "Data Warehouse" (o dataset é majoritariamente analítico/leitura)
- Deployment: "Serverless"
- OCPU/storage: usar os valores mínimos do Always Free (2 OCPU auto-scaling, 20GB) se disponível na conta — suficiente para o volume de dados deste MVP
- Definir senha do usuário `ADMIN` (essa senha vai para `ORACLE_PASSWORD`)
- Network access: "Secure access from everywhere" (mais simples para o backend acessar de fora da VCN)

- [ ] **Step 2: Baixar o wallet de conexão**

No console → instância `healthinsightdb` → "Database Connection" → "Download Wallet" (tipo "Instance Wallet"). Extrair o `.zip` para `./wallet` na raiz do projeto.

- [ ] **Step 3: Preencher o `.env`**

Copiar `.env.example` para `.env` e preencher:
- `ORACLE_USER=ADMIN`
- `ORACLE_PASSWORD=<senha definida no Step 1>`
- `ORACLE_DSN=healthinsightdb_high` (nome do serviço "high" listado em `wallet/tnsnames.ora`)
- `ORACLE_WALLET_DIR=./wallet`

- [ ] **Step 4: Verificar a conexão**

```bash
.venv\Scripts\python -c "
import oracledb
oracledb.init_oracle_client() if False else None
conn = oracledb.connect(
    user='ADMIN',
    password='<senha>',
    dsn='healthinsightdb_high',
    config_dir='./wallet',
    wallet_location='./wallet',
    wallet_password='<senha>',
)
cur = conn.cursor()
cur.execute('SELECT 1 FROM dual')
print(cur.fetchone())
conn.close()
"
```

Expected: imprime `(1,)` sem erro.

- [ ] **Step 5: Confirmar que o wallet não será commitado**

```bash
git status
```

Expected: `wallet/` não aparece em "Untracked files" listado para commit (deve estar ignorado pelo `.gitignore` da Task 0).

Nada a commitar nesta task (credenciais e wallet nunca vão para o git).

---

## Task 2: Schema do banco (DDL)

**Files:**
- Create: `sql/schema.sql`

**Interfaces:**
- Produces: tabelas `estabelecimentos`, `procedimentos`, `internacoes` que toda a ETL (Task 3-5) e as queries do backend (Task 8-10) assumem existir com esses nomes/colunas exatos.

- [ ] **Step 1: Escrever `sql/schema.sql`**

```sql
CREATE TABLE estabelecimentos (
    id             NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_cnes    VARCHAR2(20)  NOT NULL UNIQUE,
    nome           VARCHAR2(200) NOT NULL,
    municipio      VARCHAR2(120) NOT NULL,
    uf             CHAR(2)       NOT NULL,
    regiao         VARCHAR2(20)  NOT NULL,
    tipo           VARCHAR2(40),
    natureza       VARCHAR2(40),
    leitos_totais  NUMBER        NOT NULL
);

CREATE TABLE procedimentos (
    id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo   VARCHAR2(20)  NOT NULL UNIQUE,
    nome     VARCHAR2(200) NOT NULL,
    tipo     VARCHAR2(40)  NOT NULL  -- clinico, cirurgico, obstetrico, psiquiatrico, outros
);

CREATE TABLE internacoes (
    id                   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data_internacao      DATE          NOT NULL,
    estabelecimento_id   NUMBER        NOT NULL REFERENCES estabelecimentos(id),
    procedimento_id      NUMBER        NOT NULL REFERENCES procedimentos(id),
    dias_permanencia     NUMBER        NOT NULL,
    valor_total          NUMBER(12,2)
);

CREATE INDEX idx_internacoes_data  ON internacoes(data_internacao);
CREATE INDEX idx_internacoes_estab ON internacoes(estabelecimento_id);
CREATE INDEX idx_internacoes_proc  ON internacoes(procedimento_id);
```

- [ ] **Step 2: Executar o script no banco**

Via SQL Developer Web (console OCI → instância → "Database Actions" → "SQL"), colar o conteúdo de `sql/schema.sql` e executar. Alternativa via linha de comando:

```bash
.venv\Scripts\python -c "
import oracledb
conn = oracledb.connect(user='ADMIN', password='<senha>', dsn='healthinsightdb_high', config_dir='./wallet', wallet_location='./wallet', wallet_password='<senha>')
cur = conn.cursor()
for stmt in open('sql/schema.sql').read().split(';'):
    stmt = stmt.strip()
    if stmt:
        cur.execute(stmt)
conn.commit()
print('schema criado')
"
```

- [ ] **Step 3: Verificar que as 3 tabelas existem**

```sql
SELECT table_name FROM user_tables WHERE table_name IN ('ESTABELECIMENTOS', 'PROCEDIMENTOS', 'INTERNACOES');
```

Expected: 3 linhas retornadas.

- [ ] **Step 4: Commit**

```bash
git add sql/schema.sql
git commit -m "feat: schema do banco (estabelecimentos, procedimentos, internacoes)"
```

---

## Task 3: ETL — funções de tratamento (puras, testadas)

**Files:**
- Create: `etl/transform.py`
- Test: `etl/tests/test_transform.py`

**Interfaces:**
- Produces: `regiao_da_uf(uf: str) -> str`, `classificar_tipo_procedimento(codigo_cid: str) -> str`, `limpar_internacoes(df: pandas.DataFrame) -> pandas.DataFrame` — usadas pela Task 5 (load).

- [ ] **Step 1: Escrever os testes primeiro**

```python
# etl/tests/test_transform.py
import pandas as pd
import pytest
from etl.transform import regiao_da_uf, classificar_tipo_procedimento, limpar_internacoes


def test_regiao_da_uf_conhecida():
    assert regiao_da_uf("SP") == "Sudeste"
    assert regiao_da_uf("am") == "Norte"


def test_regiao_da_uf_desconhecida_levanta_erro():
    with pytest.raises(ValueError):
        regiao_da_uf("XX")


def test_classificar_tipo_procedimento():
    assert classificar_tipo_procedimento("O80") == "obstetrico"
    assert classificar_tipo_procedimento("K37") == "cirurgico"
    assert classificar_tipo_procedimento("J18") == "clinico"
    assert classificar_tipo_procedimento("F20") == "psiquiatrico"
    assert classificar_tipo_procedimento("Z99") == "outros"


def test_limpar_internacoes_remove_linhas_invalidas():
    df = pd.DataFrame({
        "data_internacao": ["2024-01-15", None, "2024-02-01", "data-invalida"],
        "codigo_cnes": ["123", "456", None, "789"],
        "codigo_procedimento": ["O80", "K37", "J18", "I50"],
        "dias_permanencia": [3, 5, 2, -1],
    })

    resultado = limpar_internacoes(df)

    assert len(resultado) == 1
    assert resultado.iloc[0]["codigo_cnes"] == "123"


def test_limpar_internacoes_normaliza_tipos():
    df = pd.DataFrame({
        "data_internacao": ["2024-01-15"],
        "codigo_cnes": [" 123 "],
        "codigo_procedimento": [" o80 "],
        "dias_permanencia": ["3"],
    })

    resultado = limpar_internacoes(df)

    assert resultado.iloc[0]["codigo_cnes"] == "123"
    assert resultado.iloc[0]["codigo_procedimento"] == "O80"
    assert resultado.iloc[0]["dias_permanencia"] == 3
    assert isinstance(resultado.iloc[0]["data_internacao"], pd.Timestamp)
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
.venv\Scripts\pytest etl/tests/test_transform.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'etl.transform'`.

- [ ] **Step 3: Implementar `etl/transform.py`**

```python
import pandas as pd

REGIAO_POR_UF = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

# Primeira letra do CID-10 -> tipo de atendimento (classificação usada nas
# telas "Análise de Atendimento" do dashboard).
PREFIXO_CID_PARA_TIPO = {
    "O": "obstetrico",   # gravidez, parto e puerpério
    "K": "cirurgico",    # aparelho digestivo — maioria dos procedimentos cirúrgicos comuns
    "J": "clinico",      # aparelho respiratório
    "I": "clinico",      # aparelho circulatório
    "F": "psiquiatrico", # transtornos mentais
}


def regiao_da_uf(uf: str) -> str:
    uf = (uf or "").strip().upper()
    if uf not in REGIAO_POR_UF:
        raise ValueError(f"UF desconhecida: {uf!r}")
    return REGIAO_POR_UF[uf]


def classificar_tipo_procedimento(codigo_cid: str) -> str:
    prefixo = (codigo_cid or "").strip().upper()[:1]
    return PREFIXO_CID_PARA_TIPO.get(prefixo, "outros")


def limpar_internacoes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df = df.dropna(subset=["data_internacao", "codigo_cnes", "codigo_procedimento", "dias_permanencia"])

    df["data_internacao"] = pd.to_datetime(df["data_internacao"], errors="coerce")
    df = df.dropna(subset=["data_internacao"])

    df["dias_permanencia"] = pd.to_numeric(df["dias_permanencia"], errors="coerce")
    df = df.dropna(subset=["dias_permanencia"])
    df = df[df["dias_permanencia"] >= 0]

    df["codigo_cnes"] = df["codigo_cnes"].astype(str).str.strip()
    df["codigo_procedimento"] = df["codigo_procedimento"].astype(str).str.strip().str.upper()

    return df.reset_index(drop=True)
```

- [ ] **Step 4: Rodar os testes para confirmar que passam**

```bash
.venv\Scripts\pytest etl/tests/test_transform.py -v
```

Expected: 5 testes, todos PASS.

- [ ] **Step 5: Commit**

```bash
git add etl/transform.py etl/tests/test_transform.py
git commit -m "feat: funcoes puras de tratamento de dados do ETL"
```

---

## Task 4: ETL — download de dados (SIH-SUS + CNES)

Envolve chamadas de rede reais a servidores do DATASUS — não é testável de forma automatizada e determinística, então a verificação é manual (rodar e inspecionar o resultado).

**Files:**
- Create: `etl/download.py`

**Interfaces:**
- Consumes: nada de outras tasks.
- Produces: `baixar_sih(uf: str, ano: int, mes: int) -> pandas.DataFrame`, `baixar_cnes(uf: str, ano: int, mes: int) -> pandas.DataFrame` — usadas pela Task 5 (load).

- [ ] **Step 1: Implementar `etl/download.py`**

```python
import pandas as pd
from pysus.online_data.SIH import download as download_sih_raw
from pysus.online_data.CNES import download as download_cnes_raw


def baixar_sih(uf: str, ano: int, mes: int) -> pd.DataFrame:
    """Baixa internações do SIH-SUS (grupo RD - Reduzida) para uma UF/mês."""
    df = download_sih_raw(uf.upper(), ano, mes, group="RD")
    return pd.DataFrame({
        "data_internacao": df["DT_INTER"],
        "codigo_cnes": df["CNES"],
        "codigo_procedimento": df["DIAG_PRINC"],
        "dias_permanencia": df["DIAS_PERM"],
        "valor_total": df.get("VAL_TOT"),
    })


def baixar_cnes(uf: str, ano: int, mes: int) -> pd.DataFrame:
    """Baixa o cadastro de estabelecimentos (CNES) para uma UF/mês."""
    df = download_cnes_raw("ST", uf.upper(), ano, mes)
    return pd.DataFrame({
        "codigo_cnes": df["CNES"],
        "nome": df["PF_PJ"].where(df["NIVATE"].isna(), df.get("NO_FANTASIA", df["PF_PJ"])),
        "municipio": df["MUNICIPIO"],
        "uf": uf.upper(),
        "tipo": df["TP_UNID"],
        "natureza": df["NAT_JUR"],
        "leitos_totais": pd.to_numeric(df.get("QT_LEITOS", 0), errors="coerce").fillna(0),
    })
```

> Nota: os nomes exatos de coluna retornados pelo `pysus` podem variar por
> versão/competência. Antes de rodar a carga real (Task 5), execute o Step 2
> abaixo e ajuste os nomes de coluna em `baixar_sih`/`baixar_cnes` conforme o
> que o `pysus` efetivamente devolver na sua versão instalada.

- [ ] **Step 2: Rodar manualmente para validar o formato**

```bash
.venv\Scripts\python -c "
from etl.download import baixar_sih, baixar_cnes
df_sih = baixar_sih('SP', 2024, 1)
print(df_sih.shape)
print(df_sih.head())
df_cnes = baixar_cnes('SP', 2024, 1)
print(df_cnes.shape)
print(df_cnes.head())
"
```

Expected: dois DataFrames não vazios impressos, sem exceção. Se os nomes de
coluna do `pysus` não baterem com o esperado (`DT_INTER`, `CNES`,
`DIAG_PRINC`, `DIAS_PERM`, etc.), ajustar `etl/download.py` até que o
resultado bata com o formato de `etl.transform.limpar_internacoes` (Task 3).

- [ ] **Step 3: Commit**

```bash
git add etl/download.py
git commit -m "feat: scripts de download SIH-SUS/CNES via pysus"
```

---

## Task 5: ETL — carga no Oracle

**Files:**
- Create: `etl/load.py`

**Interfaces:**
- Consumes: `baixar_sih`, `baixar_cnes` (Task 4), `limpar_internacoes`, `regiao_da_uf`, `classificar_tipo_procedimento` (Task 3).
- Produces: script executável `etl/load.py` que popula as 3 tabelas da Task 2. Nenhuma outra task importa deste módulo — é o ponto de entrada final do pipeline.

- [ ] **Step 1: Implementar `etl/load.py`**

```python
import os
import oracledb
import pandas as pd

from etl.download import baixar_sih, baixar_cnes
from etl.transform import limpar_internacoes, regiao_da_uf, classificar_tipo_procedimento

UFS = ["SP", "RJ", "MG", "BA", "RS", "PE", "CE", "PA", "DF", "AM"]
ANO, MES = 2024, 1


def conectar():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
        config_dir=os.environ["ORACLE_WALLET_DIR"],
        wallet_location=os.environ["ORACLE_WALLET_DIR"],
        wallet_password=os.environ["ORACLE_PASSWORD"],
    )


def carregar_estabelecimentos(conn, df_cnes: pd.DataFrame) -> dict:
    """Insere estabelecimentos e devolve {codigo_cnes: id} para uso no fato."""
    cur = conn.cursor()
    ids = {}
    for _, row in df_cnes.iterrows():
        cur.execute(
            """
            MERGE INTO estabelecimentos e
            USING (SELECT :codigo_cnes AS codigo_cnes FROM dual) src
            ON (e.codigo_cnes = src.codigo_cnes)
            WHEN NOT MATCHED THEN INSERT
                (codigo_cnes, nome, municipio, uf, regiao, tipo, natureza, leitos_totais)
                VALUES (:codigo_cnes, :nome, :municipio, :uf, :regiao, :tipo, :natureza, :leitos_totais)
            """,
            codigo_cnes=row["codigo_cnes"],
            nome=row["nome"],
            municipio=row["municipio"],
            uf=row["uf"],
            regiao=regiao_da_uf(row["uf"]),
            tipo=str(row["tipo"]),
            natureza=str(row["natureza"]),
            leitos_totais=int(row["leitos_totais"]),
        )
    conn.commit()

    cur.execute("SELECT codigo_cnes, id FROM estabelecimentos")
    return dict(cur.fetchall())


def carregar_procedimentos(conn, codigos: set[str]) -> dict:
    cur = conn.cursor()
    for codigo in codigos:
        cur.execute(
            """
            MERGE INTO procedimentos p
            USING (SELECT :codigo AS codigo FROM dual) src
            ON (p.codigo = src.codigo)
            WHEN NOT MATCHED THEN INSERT (codigo, nome, tipo)
                VALUES (:codigo, :nome, :tipo)
            """,
            codigo=codigo,
            nome=codigo,
            tipo=classificar_tipo_procedimento(codigo),
        )
    conn.commit()

    cur.execute("SELECT codigo, id FROM procedimentos")
    return dict(cur.fetchall())


def carregar_internacoes(conn, df: pd.DataFrame, mapa_estab: dict, mapa_proc: dict) -> None:
    cur = conn.cursor()
    linhas = [
        (
            row["data_internacao"].to_pydatetime(),
            mapa_estab[row["codigo_cnes"]],
            mapa_proc[row["codigo_procedimento"]],
            int(row["dias_permanencia"]),
            float(row["valor_total"]) if pd.notna(row.get("valor_total")) else None,
        )
        for _, row in df.iterrows()
        if row["codigo_cnes"] in mapa_estab and row["codigo_procedimento"] in mapa_proc
    ]
    cur.executemany(
        """
        INSERT INTO internacoes
            (data_internacao, estabelecimento_id, procedimento_id, dias_permanencia, valor_total)
        VALUES (:1, :2, :3, :4, :5)
        """,
        linhas,
    )
    conn.commit()
    print(f"{len(linhas)} internações carregadas.")


def main():
    conn = conectar()
    try:
        for uf in UFS:
            df_cnes = baixar_cnes(uf, ANO, MES)
            mapa_estab = carregar_estabelecimentos(conn, df_cnes)

            df_sih = limpar_internacoes(baixar_sih(uf, ANO, MES))
            mapa_proc = carregar_procedimentos(conn, set(df_sih["codigo_procedimento"]))

            carregar_internacoes(conn, df_sih, mapa_estab, mapa_proc)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar a carga manualmente (1 UF primeiro, para validar)**

Editar temporariamente `UFS = ["SP"]` em `etl/load.py`, então:

```bash
.venv\Scripts\python -m etl.load
```

Expected: mensagem `N internações carregadas.` sem exceção.

- [ ] **Step 3: Verificar os dados no banco**

```sql
SELECT COUNT(*) FROM estabelecimentos;
SELECT COUNT(*) FROM procedimentos;
SELECT COUNT(*) FROM internacoes;
```

Expected: as 3 contagens maiores que zero.

- [ ] **Step 4: Restaurar a lista completa de UFs e rodar a carga completa**

Reverter `UFS` para a lista completa definida no Step 1 e rodar `python -m etl.load` novamente (agora populando todas as UFs listadas).

- [ ] **Step 5: Commit**

```bash
git add etl/load.py
git commit -m "feat: script de carga ETL para o Oracle Autonomous Database"
```

---

## Task 6: Notebook de EDA + modelo preditivo

**Files:**
- Create: `notebooks/eda_modelo.ipynb`

**Interfaces:**
- Consumes: dados já carregados no banco pela Task 5 (lê via `oracledb` + `pandas.read_sql`).
- Produces: notebook com gráficos e um modelo — não é importado por nenhum código de aplicação; é evidência técnica para o repositório e para o PPT.

- [ ] **Step 1: Célula de conexão e carga em DataFrame**

```python
import os
import oracledb
import pandas as pd

conn = oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=os.environ["ORACLE_DSN"],
    config_dir=os.environ["ORACLE_WALLET_DIR"],
    wallet_location=os.environ["ORACLE_WALLET_DIR"],
    wallet_password=os.environ["ORACLE_PASSWORD"],
)

df = pd.read_sql(
    """
    SELECT i.data_internacao, i.dias_permanencia, i.valor_total,
           e.regiao, e.uf, e.tipo AS tipo_estabelecimento,
           p.tipo AS tipo_procedimento
    FROM internacoes i
    JOIN estabelecimentos e ON e.id = i.estabelecimento_id
    JOIN procedimentos p ON p.id = i.procedimento_id
    """,
    conn,
)
df["data_internacao"] = pd.to_datetime(df["data_internacao"])
df.describe(include="all")
```

- [ ] **Step 2: Célula de EDA — sazonalidade mensal**

```python
import matplotlib.pyplot as plt

df["mes"] = df["data_internacao"].dt.to_period("M")
serie_mensal = df.groupby("mes").size()

serie_mensal.plot(kind="line", marker="o", title="Internações por mês")
plt.ylabel("Internações")
plt.savefig("notebooks/output_sazonalidade_mensal.png", bbox_inches="tight")
plt.show()
```

- [ ] **Step 3: Célula de EDA — distribuição de permanência e outliers**

```python
df["dias_permanencia"].plot(kind="box", title="Distribuição de dias de permanência")
plt.savefig("notebooks/output_boxplot_permanencia.png", bbox_inches="tight")
plt.show()

limite_superior = df["dias_permanencia"].quantile(0.75) + 1.5 * (
    df["dias_permanencia"].quantile(0.75) - df["dias_permanencia"].quantile(0.25)
)
print(f"Limite superior (IQR) para outliers de permanência: {limite_superior:.1f} dias")
print(f"Casos acima do limite: {(df['dias_permanencia'] > limite_superior).sum()}")
```

- [ ] **Step 4: Célula de EDA — distribuição por região**

```python
df.groupby("regiao").size().sort_values(ascending=False).plot(
    kind="bar", title="Internações por região"
)
plt.savefig("notebooks/output_internacoes_por_regiao.png", bbox_inches="tight")
plt.show()
```

- [ ] **Step 5: Célula de modelo preditivo — regressão linear da série mensal**

```python
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

serie = serie_mensal.reset_index()
serie["mes_idx"] = range(len(serie))
serie["internacoes"] = serie[0] if 0 in serie.columns else serie.iloc[:, 1]

X = serie[["mes_idx"]].values
y = serie["internacoes"].values

modelo = LinearRegression().fit(X, y)
previsao_proximo_mes = modelo.predict([[len(serie)]])[0]

y_pred_historico = modelo.predict(X)
mae = mean_absolute_error(y, y_pred_historico)

print(f"Previsão de internações para o próximo mês: {previsao_proximo_mes:.0f}")
print(f"MAE do modelo sobre o histórico: {mae:.1f}")

plt.plot(serie["mes_idx"], y, label="Real", marker="o")
plt.plot(serie["mes_idx"], y_pred_historico, label="Tendência (regressão linear)", linestyle="--")
plt.legend()
plt.title("Previsão de internações — regressão linear sobre a série mensal")
plt.savefig("notebooks/output_previsao_internacoes.png", bbox_inches="tight")
plt.show()
```

- [ ] **Step 6: Célula de conclusão (markdown)**

```markdown
## Conclusões

- A série mensal de internações mostra [descrever o padrão observado após
  rodar com dados reais — sazonalidade, tendência de crescimento, etc.].
- O modelo de regressão linear captura a tendência geral com MAE de
  aproximadamente [valor obtido no Step 5] internações/mês, servindo como
  linha de base explicável para prever demanda no curto prazo.
- Próximos passos: comparar com um modelo de série temporal (ex. ARIMA) e
  incorporar sazonalidade explícita, se o tempo do projeto permitir.
```

> Ao rodar o notebook com os dados reais carregados pela Task 5, substituir
> os colchetes `[...]` desta célula pelos números/observações efetivamente
> obtidos — esta célula é preenchida na execução, não antes.

- [ ] **Step 7: Rodar o notebook do início ao fim**

```bash
.venv\Scripts\jupyter nbconvert --to notebook --execute notebooks/eda_modelo.ipynb --output eda_modelo.ipynb
```

Expected: executa sem erro; arquivos `notebooks/output_*.png` são gerados.

- [ ] **Step 8: Commit**

```bash
git add notebooks/eda_modelo.ipynb notebooks/output_*.png
git commit -m "feat: notebook de EDA e modelo preditivo de internacoes"
```

---

## Task 7: Backend — esqueleto FastAPI, config e pool de conexão

**Files:**
- Create: `api/__init__.py`
- Create: `api/config.py`
- Create: `api/db.py`
- Create: `api/main.py`
- Test: `api/tests/conftest.py`
- Test: `api/tests/test_health.py`

**Interfaces:**
- Produces: `settings` (objeto `Settings` em `api/config.py`), `get_connection` (dependência FastAPI em `api/db.py`), `app` (instância FastAPI em `api/main.py`) — usados por todas as tasks de router seguintes (8, 9, 10, 12) e pela task de estáticos (13).

- [ ] **Step 1: Escrever o teste do health check primeiro**

```python
# api/tests/test_health.py
def test_health_retorna_ok(client):
    resp = client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Escrever `api/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.db import get_connection


class FakeConnection:
    pass


@pytest.fixture
def client():
    app.dependency_overrides[get_connection] = lambda: FakeConnection()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 3: Rodar os testes para confirmar que falham**

```bash
.venv\Scripts\pytest api/tests/test_health.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'api.main'`.

- [ ] **Step 4: Implementar `api/__init__.py` (vazio)**

```python
```

- [ ] **Step 5: Implementar `api/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    oracle_user: str = "ADMIN"
    oracle_password: str = ""
    oracle_dsn: str = ""
    oracle_wallet_dir: str = "./wallet"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 6: Implementar `api/db.py`**

```python
import oracledb

from api.config import settings

_pool: oracledb.ConnectionPool | None = None


def _get_pool() -> oracledb.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=settings.oracle_user,
            password=settings.oracle_password,
            dsn=settings.oracle_dsn,
            config_dir=settings.oracle_wallet_dir,
            wallet_location=settings.oracle_wallet_dir,
            wallet_password=settings.oracle_password,
            min=1,
            max=4,
            increment=1,
        )
    return _pool


def get_connection():
    pool = _get_pool()
    conn = pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)
```

- [ ] **Step 7: Implementar `api/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="HealthInsight API")


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Rodar os testes para confirmar que passam**

```bash
.venv\Scripts\pytest api/tests/test_health.py -v
```

Expected: 1 teste PASS.

- [ ] **Step 9: Commit**

```bash
git add api/__init__.py api/config.py api/db.py api/main.py api/tests/conftest.py api/tests/test_health.py
git commit -m "feat: esqueleto da API FastAPI com config e pool de conexao Oracle"
```

---

## Task 8: Backend — endpoints da tela "Visão Geral"

**Files:**
- Create: `api/queries/__init__.py`
- Create: `api/queries/visao_geral.py`
- Create: `api/routers/__init__.py`
- Create: `api/routers/visao_geral.py`
- Modify: `api/main.py` (registrar o router)
- Test: `api/tests/test_visao_geral.py`

**Interfaces:**
- Consumes: `get_connection` (Task 7).
- Produces: rotas `GET /api/kpis`, `GET /api/tendencia-mensal`, `GET /api/leitos-regiao`, registradas em `app` (Task 7) via `app.include_router`.

- [ ] **Step 1: Escrever os testes primeiro**

```python
# api/tests/test_visao_geral.py
from api.routers import visao_geral as router_module


def test_kpis_endpoint(client, monkeypatch):
    def fake_get_kpis(conn, ano):
        assert ano == 2024
        return {
            "total_internacoes": 1284730,
            "permanencia_media": 5.3,
            "leitos_disponiveis": 48210,
            "taxa_ocupacao": 74.6,
        }

    monkeypatch.setattr(router_module.q, "get_kpis", fake_get_kpis)

    resp = client.get("/api/kpis?ano=2024")

    assert resp.status_code == 200
    assert resp.json()["taxa_ocupacao"] == 74.6


def test_tendencia_mensal_endpoint(client, monkeypatch):
    def fake_get_tendencia_mensal(conn, ano):
        return [{"mes": 1, "total": 98000}, {"mes": 2, "total": 102000}]

    monkeypatch.setattr(router_module.q, "get_tendencia_mensal", fake_get_tendencia_mensal)

    resp = client.get("/api/tendencia-mensal?ano=2024")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_leitos_regiao_endpoint(client, monkeypatch):
    def fake_get_leitos_regiao(conn, ano):
        return [{"regiao": "Sudeste", "ocupados": 18200, "disponiveis": 5800}]

    monkeypatch.setattr(router_module.q, "get_leitos_regiao", fake_get_leitos_regiao)

    resp = client.get("/api/leitos-regiao?ano=2024")

    assert resp.status_code == 200
    assert resp.json()[0]["regiao"] == "Sudeste"
```

Também um teste de unidade para a lógica de cálculo de ocupação (censo médio diário), que não depende do FastAPI:

```python
# api/tests/test_queries_visao_geral.py
from unittest.mock import MagicMock
from api.queries.visao_geral import get_kpis


def test_get_kpis_calcula_taxa_ocupacao_por_censo_medio():
    conn = MagicMock()
    cursor = conn.cursor.return_value
    # 1a query: total_internacoes, permanencia_media, soma_dias
    # 2a query: leitos_totais
    cursor.fetchone.side_effect = [
        (1000, 5.0, 5000),  # soma_dias = 5000 dias-paciente no ano
        (100,),              # 100 leitos totais na rede
    ]

    resultado = get_kpis(conn, 2024)

    # censo medio diario = 5000 / 366 (2024 e bissexto) ~= 13.66
    # taxa ocupacao = 13.66 / 100 * 100 ~= 13.7%
    assert resultado["total_internacoes"] == 1000
    assert resultado["permanencia_media"] == 5.0
    assert resultado["taxa_ocupacao"] == 13.7
    assert resultado["leitos_disponiveis"] == 86
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
.venv\Scripts\pytest api/tests/test_visao_geral.py api/tests/test_queries_visao_geral.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'api.queries'`.

- [ ] **Step 3: Implementar `api/queries/__init__.py` (vazio)**

```python
```

- [ ] **Step 4: Implementar `api/queries/visao_geral.py`**

```python
def get_kpis(conn, ano: int) -> dict:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*), AVG(dias_permanencia), SUM(dias_permanencia)
        FROM internacoes
        WHERE EXTRACT(YEAR FROM data_internacao) = :ano
        """,
        ano=ano,
    )
    total_internacoes, permanencia_media, soma_dias = cur.fetchone()
    total_internacoes = total_internacoes or 0
    permanencia_media = float(permanencia_media or 0)
    soma_dias = float(soma_dias or 0)

    cur.execute("SELECT SUM(leitos_totais) FROM estabelecimentos")
    leitos_totais = cur.fetchone()[0] or 0

    dias_no_ano = 366 if ano % 4 == 0 else 365
    # Censo médio diário = dias-paciente no período / dias de calendário —
    # estimativa padrão de ocupação média a partir de dados de admissão.
    censo_medio_diario = soma_dias / dias_no_ano
    taxa_ocupacao = round((censo_medio_diario / leitos_totais) * 100, 1) if leitos_totais else 0
    leitos_disponiveis = max(int(leitos_totais - round(censo_medio_diario)), 0)

    return {
        "total_internacoes": total_internacoes,
        "permanencia_media": round(permanencia_media, 1),
        "leitos_disponiveis": leitos_disponiveis,
        "taxa_ocupacao": taxa_ocupacao,
    }


def get_tendencia_mensal(conn, ano: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT EXTRACT(MONTH FROM data_internacao) AS mes, COUNT(*) AS total
        FROM internacoes
        WHERE EXTRACT(YEAR FROM data_internacao) = :ano
        GROUP BY EXTRACT(MONTH FROM data_internacao)
        ORDER BY mes
        """,
        ano=ano,
    )
    return [{"mes": int(mes), "total": total} for mes, total in cur.fetchall()]


def get_leitos_regiao(conn, ano: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.regiao, SUM(e.leitos_totais) AS leitos_totais, SUM(i.dias_permanencia) AS soma_dias
        FROM estabelecimentos e
        JOIN internacoes i ON i.estabelecimento_id = e.id
        WHERE EXTRACT(YEAR FROM i.data_internacao) = :ano
        GROUP BY e.regiao
        """,
        ano=ano,
    )
    dias_no_ano = 366 if ano % 4 == 0 else 365
    resultado = []
    for regiao, leitos_totais, soma_dias in cur.fetchall():
        ocupados = round((soma_dias or 0) / dias_no_ano)
        resultado.append({
            "regiao": regiao,
            "ocupados": ocupados,
            "disponiveis": max(int(leitos_totais or 0) - ocupados, 0),
        })
    return resultado
```

- [ ] **Step 5: Implementar `api/routers/__init__.py` (vazio)**

```python
```

- [ ] **Step 6: Implementar `api/routers/visao_geral.py`**

```python
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
```

- [ ] **Step 7: Registrar o router em `api/main.py`**

```python
from fastapi import FastAPI

from api.routers import visao_geral

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Rodar os testes para confirmar que passam**

```bash
.venv\Scripts\pytest api/tests/test_visao_geral.py api/tests/test_queries_visao_geral.py -v
```

Expected: 4 testes, todos PASS.

- [ ] **Step 9: Commit**

```bash
git add api/queries api/routers/visao_geral.py api/main.py api/tests/test_visao_geral.py api/tests/test_queries_visao_geral.py
git commit -m "feat: endpoints da tela Visao Geral (kpis, tendencia mensal, leitos por regiao)"
```

---

## Task 9: Backend — endpoints da tela "Capacidade Hospitalar"

**Files:**
- Create: `api/queries/capacidade.py`
- Create: `api/routers/capacidade.py`
- Modify: `api/main.py` (registrar o router)
- Test: `api/tests/test_capacidade.py`

**Interfaces:**
- Consumes: `get_connection` (Task 7).
- Produces: rotas `GET /api/ocupacao-estados`, `GET /api/hospitais`.

- [ ] **Step 1: Escrever os testes primeiro**

```python
# api/tests/test_capacidade.py
from api.routers import capacidade as router_module


def test_ocupacao_estados_endpoint(client, monkeypatch):
    def fake_get_ocupacao_estados(conn, ano):
        return [{"uf": "SP", "taxa_ocupacao": 82.1, "internacoes": 300000}]

    monkeypatch.setattr(router_module.q, "get_ocupacao_estados", fake_get_ocupacao_estados)

    resp = client.get("/api/ocupacao-estados?ano=2024")

    assert resp.status_code == 200
    assert resp.json()[0]["uf"] == "SP"


def test_hospitais_endpoint_aplica_filtros(client, monkeypatch):
    capturado = {}

    def fake_get_hospitais(conn, ano, regiao, tipo):
        capturado["regiao"] = regiao
        capturado["tipo"] = tipo
        return [{
            "nome": "Hospital das Clínicas SP",
            "municipio": "São Paulo",
            "regiao": "Sudeste",
            "internacoes": 42810,
            "permanencia_media": 6.2,
            "taxa_ocupacao": 93.0,
            "status": "critico",
        }]

    monkeypatch.setattr(router_module.q, "get_hospitais", fake_get_hospitais)

    resp = client.get("/api/hospitais?ano=2024&regiao=Sudeste&tipo=Hospital")

    assert resp.status_code == 200
    assert capturado == {"regiao": "Sudeste", "tipo": "Hospital"}
    assert resp.json()[0]["status"] == "critico"
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
.venv\Scripts\pytest api/tests/test_capacidade.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'api.routers.capacidade'`.

- [ ] **Step 3: Implementar `api/queries/capacidade.py`**

```python
def get_ocupacao_estados(conn, ano: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT e.uf, SUM(e.leitos_totais) AS leitos_totais,
               SUM(i.dias_permanencia) AS soma_dias, COUNT(i.id) AS internacoes
        FROM estabelecimentos e
        JOIN internacoes i ON i.estabelecimento_id = e.id
        WHERE EXTRACT(YEAR FROM i.data_internacao) = :ano
        GROUP BY e.uf
        """,
        ano=ano,
    )
    dias_no_ano = 366 if ano % 4 == 0 else 365
    resultado = []
    for uf, leitos_totais, soma_dias, internacoes in cur.fetchall():
        censo_medio = (soma_dias or 0) / dias_no_ano
        taxa = round((censo_medio / leitos_totais) * 100, 1) if leitos_totais else 0
        resultado.append({"uf": uf, "taxa_ocupacao": taxa, "internacoes": internacoes})
    return resultado


def _status_por_ocupacao(taxa: float) -> str:
    if taxa >= 90:
        return "critico"
    if taxa >= 80:
        return "atencao"
    return "normal"


def get_hospitais(conn, ano: int, regiao: str | None, tipo: str | None) -> list[dict]:
    cur = conn.cursor()
    condicoes = ["EXTRACT(YEAR FROM i.data_internacao) = :ano"]
    params = {"ano": ano}
    if regiao:
        condicoes.append("e.regiao = :regiao")
        params["regiao"] = regiao
    if tipo:
        condicoes.append("e.tipo = :tipo")
        params["tipo"] = tipo

    cur.execute(
        f"""
        SELECT e.nome, e.municipio, e.regiao, e.leitos_totais,
               COUNT(i.id) AS internacoes, AVG(i.dias_permanencia) AS permanencia_media,
               SUM(i.dias_permanencia) AS soma_dias
        FROM estabelecimentos e
        JOIN internacoes i ON i.estabelecimento_id = e.id
        WHERE {' AND '.join(condicoes)}
        GROUP BY e.nome, e.municipio, e.regiao, e.leitos_totais
        """,
        params,
    )
    dias_no_ano = 366 if ano % 4 == 0 else 365
    resultado = []
    for nome, municipio, regiao_, leitos_totais, internacoes, permanencia_media, soma_dias in cur.fetchall():
        censo_medio = (soma_dias or 0) / dias_no_ano
        taxa = round((censo_medio / leitos_totais) * 100, 1) if leitos_totais else 0
        resultado.append({
            "nome": nome,
            "municipio": municipio,
            "regiao": regiao_,
            "internacoes": internacoes,
            "permanencia_media": round(float(permanencia_media or 0), 1),
            "taxa_ocupacao": taxa,
            "status": _status_por_ocupacao(taxa),
        })
    return resultado
```

- [ ] **Step 4: Implementar `api/routers/capacidade.py`**

```python
from fastapi import APIRouter, Depends

from api.db import get_connection
from api.queries import capacidade as q

router = APIRouter(prefix="/api", tags=["capacidade"])


@router.get("/ocupacao-estados")
def ocupacao_estados(ano: int = 2024, conn=Depends(get_connection)):
    return q.get_ocupacao_estados(conn, ano)


@router.get("/hospitais")
def hospitais(
    ano: int = 2024,
    regiao: str | None = None,
    tipo: str | None = None,
    conn=Depends(get_connection),
):
    return q.get_hospitais(conn, ano, regiao, tipo)
```

- [ ] **Step 5: Registrar o router em `api/main.py`**

```python
from fastapi import FastAPI

from api.routers import visao_geral, capacidade

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)
app.include_router(capacidade.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Rodar os testes para confirmar que passam**

```bash
.venv\Scripts\pytest api/tests/test_capacidade.py -v
```

Expected: 2 testes PASS.

- [ ] **Step 7: Commit**

```bash
git add api/queries/capacidade.py api/routers/capacidade.py api/main.py api/tests/test_capacidade.py
git commit -m "feat: endpoints da tela Capacidade Hospitalar (ocupacao por UF e tabela de hospitais)"
```

---

## Task 10: Backend — endpoint da tela "Análise de Atendimento"

**Files:**
- Create: `api/queries/atendimento.py`
- Create: `api/routers/atendimento.py`
- Modify: `api/main.py` (registrar o router)
- Test: `api/tests/test_atendimento.py`

**Interfaces:**
- Consumes: `get_connection` (Task 7).
- Produces: rota `GET /api/tipos-atendimento`.

- [ ] **Step 1: Escrever o teste primeiro**

```python
# api/tests/test_atendimento.py
from api.routers import atendimento as router_module


def test_tipos_atendimento_endpoint(client, monkeypatch):
    def fake_get_tipos_atendimento(conn, ano):
        return {
            "distribuicao": [{"tipo": "clinico", "percentual": 38.0}],
            "top_procedimentos": [{
                "codigo": "O80", "nome": "O80", "tipo": "obstetrico",
                "internacoes": 198440, "permanencia_media": 2.1,
            }],
        }

    monkeypatch.setattr(router_module.q, "get_tipos_atendimento", fake_get_tipos_atendimento)

    resp = client.get("/api/tipos-atendimento?ano=2024")

    assert resp.status_code == 200
    body = resp.json()
    assert body["distribuicao"][0]["tipo"] == "clinico"
    assert body["top_procedimentos"][0]["codigo"] == "O80"
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
.venv\Scripts\pytest api/tests/test_atendimento.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'api.routers.atendimento'`.

- [ ] **Step 3: Implementar `api/queries/atendimento.py`**

```python
def get_tipos_atendimento(conn, ano: int) -> dict:
    cur = conn.cursor()

    cur.execute(
        """
        SELECT p.tipo, COUNT(*) AS total
        FROM internacoes i
        JOIN procedimentos p ON p.id = i.procedimento_id
        WHERE EXTRACT(YEAR FROM i.data_internacao) = :ano
        GROUP BY p.tipo
        """,
        ano=ano,
    )
    linhas = cur.fetchall()
    total_geral = sum(total for _, total in linhas) or 1
    distribuicao = [
        {"tipo": tipo, "percentual": round(total / total_geral * 100, 1)}
        for tipo, total in linhas
    ]

    cur.execute(
        """
        SELECT p.codigo, p.nome, p.tipo, COUNT(*) AS internacoes,
               AVG(i.dias_permanencia) AS permanencia_media
        FROM internacoes i
        JOIN procedimentos p ON p.id = i.procedimento_id
        WHERE EXTRACT(YEAR FROM i.data_internacao) = :ano
        GROUP BY p.codigo, p.nome, p.tipo
        ORDER BY COUNT(*) DESC
        FETCH FIRST 5 ROWS ONLY
        """,
        ano=ano,
    )
    top_procedimentos = [
        {
            "codigo": codigo,
            "nome": nome,
            "tipo": tipo,
            "internacoes": internacoes,
            "permanencia_media": round(float(permanencia_media or 0), 1),
        }
        for codigo, nome, tipo, internacoes, permanencia_media in cur.fetchall()
    ]

    return {"distribuicao": distribuicao, "top_procedimentos": top_procedimentos}
```

- [ ] **Step 4: Implementar `api/routers/atendimento.py`**

```python
from fastapi import APIRouter, Depends

from api.db import get_connection
from api.queries import atendimento as q

router = APIRouter(prefix="/api", tags=["atendimento"])


@router.get("/tipos-atendimento")
def tipos_atendimento(ano: int = 2024, conn=Depends(get_connection)):
    return q.get_tipos_atendimento(conn, ano)
```

- [ ] **Step 5: Registrar o router em `api/main.py`**

```python
from fastapi import FastAPI

from api.routers import visao_geral, capacidade, atendimento

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)
app.include_router(capacidade.router)
app.include_router(atendimento.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Rodar o teste para confirmar que passa**

```bash
.venv\Scripts\pytest api/tests/test_atendimento.py -v
```

Expected: 1 teste PASS.

- [ ] **Step 7: Commit**

```bash
git add api/queries/atendimento.py api/routers/atendimento.py api/main.py api/tests/test_atendimento.py
git commit -m "feat: endpoint da tela Analise de Atendimento (distribuicao por tipo e top procedimentos)"
```

---

## Task 11: Select AI — configuração no Oracle Autonomous Database

Task manual (SQL Developer Web / Database Actions) — sem código Python, mas com verificação executável.

**Files:**
- Create: `sql/select_ai_setup.sql`

**Interfaces:**
- Produces: perfil Select AI `HEALTHINSIGHT_PROFILE` no banco, usado pela Task 12.

- [ ] **Step 1: Escrever `sql/select_ai_setup.sql`**

```sql
BEGIN
  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => 'OCI_GENAI_CRED',
    username        => NULL,
    password        => NULL,
    -- Credencial baseada em OCI Resource Principal/API Key configurada
    -- na Compute Instance ou via chave de API do usuário administrador.
    -- Ver documentação: "Select AI Credentials" no console OCI.
    params          => JSON_OBJECT('comp_ocid' VALUE '<OCID_DO_COMPARTMENT>')
  );
END;
/

BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'HEALTHINSIGHT_PROFILE',
    attributes   => '{
      "provider": "oci",
      "credential_name": "OCI_GENAI_CRED",
      "object_list": [
        {"owner": "ADMIN", "name": "ESTABELECIMENTOS"},
        {"owner": "ADMIN", "name": "PROCEDIMENTOS"},
        {"owner": "ADMIN", "name": "INTERNACOES"}
      ]
    }'
  );
END;
/
```

- [ ] **Step 2: Executar no SQL Developer Web**

Console OCI → instância `healthinsightdb` → "Database Actions" → "SQL". Colar e
executar o conteúdo de `sql/select_ai_setup.sql`, substituindo
`<OCID_DO_COMPARTMENT>` pelo OCID real do compartment usado no projeto
(visível no console OCI, canto superior de qualquer recurso).

- [ ] **Step 3: Verificar que o perfil responde**

No mesmo SQL Worksheet:

```sql
SELECT DBMS_CLOUD_AI.GENERATE(
  prompt       => 'Quantas internações existem no total?',
  profile_name => 'HEALTHINSIGHT_PROFILE',
  action       => 'runsql'
) FROM dual;
```

Expected: retorna um valor numérico (contagem de linhas de `internacoes`)
sem erro.

Nada a commitar em código de aplicação além do script SQL:

- [ ] **Step 4: Commit**

```bash
git add sql/select_ai_setup.sql
git commit -m "feat: script de configuracao do perfil Select AI"
```

---

## Task 12: Backend — endpoint `/api/ai/query`

**Files:**
- Create: `api/queries/ai.py`
- Create: `api/routers/ai.py`
- Modify: `api/main.py` (registrar o router)
- Test: `api/tests/test_ai.py`

**Interfaces:**
- Consumes: `get_connection` (Task 7); perfil `HEALTHINSIGHT_PROFILE` (Task 11).
- Produces: rota `POST /api/ai/query`, que substitui a função `runAI()`/`getKey()` do front-end (Task 15).

- [ ] **Step 1: Escrever o teste primeiro**

```python
# api/tests/test_ai.py
from api.routers import ai as router_module


def test_ai_query_endpoint(client, monkeypatch):
    def fake_perguntar(conn, pergunta):
        assert pergunta == "Qual região teve maior crescimento?"
        return {"resposta": "A região Norte cresceu 14,2%.", "dados": "[]"}

    monkeypatch.setattr(router_module.q, "perguntar", fake_perguntar)

    resp = client.post("/api/ai/query", json={"pergunta": "Qual região teve maior crescimento?"})

    assert resp.status_code == 200
    assert "Norte" in resp.json()["resposta"]


def test_ai_query_endpoint_rejeita_pergunta_vazia(client):
    resp = client.post("/api/ai/query", json={"pergunta": ""})

    assert resp.status_code == 422
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
.venv\Scripts\pytest api/tests/test_ai.py -v
```

Expected: FAIL com `ModuleNotFoundError: No module named 'api.routers.ai'`.

- [ ] **Step 3: Implementar `api/queries/ai.py`**

```python
def perguntar(conn, pergunta: str) -> dict:
    cur = conn.cursor()

    cur.execute(
        """
        SELECT DBMS_CLOUD_AI.GENERATE(
            prompt       => :pergunta,
            profile_name => 'HEALTHINSIGHT_PROFILE',
            action       => 'narrate'
        ) FROM dual
        """,
        pergunta=pergunta,
    )
    resposta_raw = cur.fetchone()[0]
    resposta = resposta_raw.read() if hasattr(resposta_raw, "read") else str(resposta_raw)

    cur.execute(
        """
        SELECT DBMS_CLOUD_AI.GENERATE(
            prompt       => :pergunta,
            profile_name => 'HEALTHINSIGHT_PROFILE',
            action       => 'runsql'
        ) FROM dual
        """,
        pergunta=pergunta,
    )
    dados_raw = cur.fetchone()[0]
    dados = dados_raw.read() if hasattr(dados_raw, "read") else str(dados_raw)

    return {"resposta": resposta, "dados": dados}
```

- [ ] **Step 4: Implementar `api/routers/ai.py`**

```python
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
```

- [ ] **Step 5: Registrar o router em `api/main.py`**

```python
from fastapi import FastAPI

from api.routers import visao_geral, capacidade, atendimento, ai

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)
app.include_router(capacidade.router)
app.include_router(atendimento.router)
app.include_router(ai.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Rodar os testes para confirmar que passam**

```bash
.venv\Scripts\pytest api/tests/test_ai.py -v
```

Expected: 2 testes PASS.

- [ ] **Step 7: Commit**

```bash
git add api/queries/ai.py api/routers/ai.py api/main.py api/tests/test_ai.py
git commit -m "feat: endpoint /api/ai/query integrando Oracle Select AI"
```

---

## Task 13: Backend — servir o front-end estático

**Files:**
- Modify: mover `index.html` (raiz) para `api/static/index.html` (`git mv`)
- Modify: `api/main.py` (montar estáticos e servir `index.html` na raiz)

**Interfaces:**
- Consumes: `app` (Task 7).
- Produces: `GET /` servindo `api/static/index.html`; base para as Tasks 14 e 15 editarem o arquivo em seu novo local.

- [ ] **Step 1: Mover o arquivo preservando histórico**

```bash
git mv index.html api/static/index.html
```

- [ ] **Step 2: Modificar `api/main.py`**

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse

from api.routers import visao_geral, capacidade, atendimento, ai

app = FastAPI(title="HealthInsight API")
app.include_router(visao_geral.router)
app.include_router(capacidade.router)
app.include_router(atendimento.router)
app.include_router(ai.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse("api/static/index.html")
```

- [ ] **Step 3: Rodar a API localmente e verificar manualmente**

```bash
.venv\Scripts\uvicorn api.main:app --reload
```

Abrir `http://localhost:8000/` no navegador.

Expected: o dashboard (com o design atual) é exibido.

- [ ] **Step 4: Rodar a suíte de testes completa para garantir que nada quebrou**

```bash
.venv\Scripts\pytest api/tests -v
```

Expected: todos os testes anteriores continuam PASS.

- [ ] **Step 5: Commit**

```bash
git add api/main.py api/static/index.html
git commit -m "feat: servir o front-end estatico a partir da API FastAPI"
```

---

## Task 14: Front-end — dashboards consumindo a API real

**Files:**
- Modify: `api/static/index.html` (bloco `<script>` dos gráficos das telas Visão Geral, Capacidade Hospitalar e Análise de Atendimento)

**Interfaces:**
- Consumes: `GET /api/kpis`, `GET /api/tendencia-mensal`, `GET /api/leitos-regiao`, `GET /api/ocupacao-estados`, `GET /api/hospitais`, `GET /api/tipos-atendimento` (Tasks 8, 9, 10).

- [ ] **Step 1: Substituir a inicialização dos KPIs e do gráfico de tendência**

No `<script>` de `api/static/index.html`, localizar o bloco que cria
`trendChart` a partir do array fixo `months`/dados hardcoded e os `<div
class="kpi-value">` estáticos do HTML. Substituir por:

```html
<!-- No HTML dos KPIs, adicionar ids: -->
<div class="kpi-value" id="kpiTotalInternacoes">—</div>
...
<div class="kpi-value" id="kpiPermanenciaMedia">—</div>
...
<div class="kpi-value" id="kpiLeitosDisponiveis">—</div>
...
<div class="kpi-value" id="kpiTaxaOcupacao">—</div>
```

```javascript
async function carregarKpis() {
  const resp = await fetch('/api/kpis?ano=2024');
  const data = await resp.json();
  document.getElementById('kpiTotalInternacoes').textContent = data.total_internacoes.toLocaleString('pt-BR');
  document.getElementById('kpiPermanenciaMedia').textContent = `${data.permanencia_media} dias`;
  document.getElementById('kpiLeitosDisponiveis').textContent = data.leitos_disponiveis.toLocaleString('pt-BR');
  document.getElementById('kpiTaxaOcupacao').textContent = `${data.taxa_ocupacao}%`;
}

async function carregarTendenciaMensal() {
  const resp = await fetch('/api/tendencia-mensal?ano=2024');
  const data = await resp.json();
  const labels = data.map(d => months[d.mes - 1]);
  const valores = data.map(d => d.total);

  new Chart(document.getElementById('trendChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '2024', data: valores, borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.06)', fill: true, tension: 0.4,
        borderWidth: 2, pointRadius: 2, pointBackgroundColor: '#3b82f6',
      }],
    },
    options: baseOpts({}),
  });
}

carregarKpis();
carregarTendenciaMensal();
```

- [ ] **Step 2: Substituir a inicialização do gráfico de leitos por região**

Remover a chamada original `new Chart(document.getElementById('bedChart'), ...)` com arrays fixos e substituir por:

```javascript
async function carregarLeitosRegiao() {
  const resp = await fetch('/api/leitos-regiao?ano=2024');
  const data = await resp.json();

  new Chart(document.getElementById('bedChart'), {
    type: 'bar',
    data: {
      labels: data.map(d => d.regiao),
      datasets: [
        { label: 'Ocupados', data: data.map(d => d.ocupados), backgroundColor: '#3b82f6', borderRadius: 3 },
        { label: 'Disponíveis', data: data.map(d => d.disponiveis), backgroundColor: '#1e3a5f', borderRadius: 3 },
      ],
    },
    options: baseOpts({}),
  });
}

carregarLeitosRegiao();
```

- [ ] **Step 3: Substituir a tabela e o mapa da tela "Capacidade Hospitalar"**

Remover as linhas `<tr>` hardcoded do `<tbody>` da tabela de estabelecimentos
e o preenchimento estático das cores do mapa; substituir por:

```javascript
async function carregarHospitais() {
  const resp = await fetch('/api/hospitais?ano=2024');
  const hospitais = await resp.json();
  const tbody = document.querySelector('#s2 tbody');
  tbody.innerHTML = hospitais.map(h => `
    <tr>
      <td><div class="hosp-name">${h.nome}</div></td>
      <td>${h.municipio}</td><td>${h.regiao}</td><td>${h.internacoes.toLocaleString('pt-BR')}</td>
      <td>${h.permanencia_media} dias</td>
      <td><div class="occ-wrap"><div class="occ-bar"><div class="occ-fill" style="width:${h.taxa_ocupacao}%;background:${corPorStatus(h.status)};"></div></div>
      <div class="occ-val" style="color:${corPorStatus(h.status)};">${h.taxa_ocupacao}%</div></div></td>
      <td><span class="badge ${badgePorStatus(h.status)}">${rotuloPorStatus(h.status)}</span></td>
    </tr>
  `).join('');
}

function corPorStatus(status) {
  return { critico: '#ef4444', atencao: '#f59e0b', normal: '#22c55e' }[status];
}
function badgePorStatus(status) {
  return { critico: 'badge-red', atencao: 'badge-amber', normal: 'badge-green' }[status];
}
function rotuloPorStatus(status) {
  return { critico: 'Crítico', atencao: 'Atenção', normal: 'Normal' }[status];
}

async function carregarOcupacaoEstados() {
  const resp = await fetch('/api/ocupacao-estados?ano=2024');
  const estados = await resp.json();
  estados.forEach(e => {
    const path = document.getElementById(e.uf);
    if (path) path.style.fill = corPorOcupacao(e.taxa_ocupacao);
  });
}

function corPorOcupacao(taxa) {
  if (taxa >= 90) return '#ef4444';
  if (taxa >= 75) return '#f59e0b';
  return '#3b82f6';
}

carregarHospitais();
carregarOcupacaoEstados();
```

- [ ] **Step 4: Substituir os gráficos da tela "Análise de Atendimento"**

Remover a inicialização fixa de `pieChart` e a tabela de "Top procedimentos"; substituir por:

```javascript
async function carregarTiposAtendimento() {
  const resp = await fetch('/api/tipos-atendimento?ano=2024');
  const data = await resp.json();

  new Chart(document.getElementById('pieChart'), {
    type: 'doughnut',
    data: {
      labels: data.distribuicao.map(d => d.tipo),
      datasets: [{
        data: data.distribuicao.map(d => d.percentual),
        backgroundColor: ['#3b82f6', '#a78bfa', '#22c55e', '#f59e0b', '#ef4444'],
        borderWidth: 0,
      }],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, cutout: '60%' },
  });

  const tbody = document.querySelector('#s3 tbody');
  tbody.innerHTML = data.top_procedimentos.map(p => `
    <tr><td>${p.nome}</td><td><span class="badge type-${p.tipo}">${p.tipo}</span></td>
    <td>${p.internacoes.toLocaleString('pt-BR')}</td><td>—</td><td>${p.permanencia_media} dias</td></tr>
  `).join('');
}

carregarTiposAtendimento();
```

> O gráfico `growthChart` (crescimento por tipo em 24 meses) permanece fora
> de escopo desta task — não há endpoint correspondente no plano; se sobrar
> tempo, é uma extensão natural de `api/queries/atendimento.py` seguindo o
> mesmo padrão dos demais.

- [ ] **Step 5: Remover o código morto correspondente**

Apagar, no `<script>` original, os blocos de criação de `trendChart`,
`bedChart`, `pieChart` e as linhas `<tr>` estáticas que foram substituídos
pelos passos acima, para não sobrar código inacessível.

- [ ] **Step 6: Verificar manualmente no navegador**

Com a API rodando (`uvicorn api.main:app --reload`) e o banco populado
(Task 5), abrir `http://localhost:8000/` e navegar pelas 3 telas
substituídas.

Expected: KPIs, gráficos, mapa e tabelas exibem os dados reais carregados
no banco (não mais os números de exemplo do mockup original).

- [ ] **Step 7: Commit**

```bash
git add api/static/index.html
git commit -m "feat: dashboards consumindo dados reais via API"
```

---

## Task 15: Front-end — tela "Oracle Select AI" com IA real

**Files:**
- Modify: `api/static/index.html` (funções `runAI`, `fillQ`, remoção de `getKey`/`aiAnswers`)

**Interfaces:**
- Consumes: `POST /api/ai/query` (Task 12).

- [ ] **Step 1: Remover o mock**

Apagar do `<script>` de `api/static/index.html` o objeto `aiAnswers` e a
função `getKey()` inteiros — não são mais necessários.

- [ ] **Step 2: Reescrever `runAI()` para chamar a API real**

```javascript
async function runAI() {
  const q = document.getElementById('aiInput').value.trim();
  if (!q) return;
  const resp = document.getElementById('aiResponse');
  resp.innerHTML = `<div class="ai-thinking"><div class="dots"><span></span><span></span><span></span></div>&nbsp; Consultando base de dados via Oracle Select AI...</div>`;

  try {
    const apiResp = await fetch('/api/ai/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pergunta: q }),
    });
    if (!apiResp.ok) throw new Error(`HTTP ${apiResp.status}`);
    const data = await apiResp.json();

    resp.innerHTML = `<div class="ai-answer">${data.resposta}<div class="source">Oracle Select AI — SIH-SUS/DATASUS</div></div>`;
    atualizarGraficoAI(data.dados);
  } catch (err) {
    resp.innerHTML = `<div class="ai-answer">Não foi possível consultar o Select AI agora. Tente novamente em instantes.<div class="source">Erro: ${err.message}</div></div>`;
  }
}

function atualizarGraficoAI(dadosJson) {
  let linhas;
  try {
    linhas = JSON.parse(dadosJson);
  } catch {
    return; // resposta não tabular — sem gráfico para esta pergunta
  }
  if (!Array.isArray(linhas) || linhas.length === 0) return;

  const chaves = Object.keys(linhas[0]);
  const [chaveLabel, chaveValor] = chaves;

  aiChartInst.destroy();
  aiChartInst = new Chart(document.getElementById('aiChart'), {
    type: 'bar',
    data: {
      labels: linhas.map(l => l[chaveLabel]),
      datasets: [{ label: chaveValor, data: linhas.map(l => l[chaveValor]), backgroundColor: '#3b82f6', borderRadius: 4, borderWidth: 0 }],
    },
    options: { ...baseOpts({ indexAxis: 'y' }) },
  });
}
```

`fillQ()` continua igual (só preenche o input e chama `runAI()`).

- [ ] **Step 3: Verificar manualmente**

Com a API e o Select AI configurados (Tasks 11-12), abrir a tela "Oracle
Select AI" no navegador, clicar em um dos chips de exemplo.

Expected: aparece o indicador de "consultando", depois uma resposta gerada
pelo Select AI real (texto diferente a cada nova pergunta, não mais um dos
6 textos fixos do mock original).

- [ ] **Step 4: Commit**

```bash
git add api/static/index.html
git commit -m "feat: tela Oracle Select AI consumindo IA real via /api/ai/query"
```

---

## Task 16: Deploy — provisionar a Compute Instance

Task manual (console/CLI OCI) — sem código de aplicação.

**Files:**
- Create: `deploy/healthinsight-api.service` (unit file do systemd)
- Create: `deploy/nginx-healthinsight.conf`

**Interfaces:**
- Produces: Compute Instance acessível via SSH, com Python 3.11 e o repositório clonado — base para a Task 17.

- [ ] **Step 1: Criar a instância**

Console OCI → Compute → Instances → Create Instance:
- Imagem: "Canonical Ubuntu 22.04"
- Shape: `VM.Standard.E2.1.Micro` (Always Free, se disponível na conta)
- Adicionar chave SSH pública do desenvolvedor
- Anotar o IP público atribuído

- [ ] **Step 2: Liberar a porta 80 no Security List/NSG**

Console OCI → VCN da instância → Security Lists → adicionar Ingress Rule:
Source `0.0.0.0/0`, protocolo TCP, porta destino `80`.

- [ ] **Step 3: Conectar via SSH e instalar dependências do sistema**

```bash
ssh ubuntu@<IP_PUBLICO>
sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx git
```

- [ ] **Step 4: Clonar o repositório na instância**

```bash
git clone https://github.com/guilhermeesu5/Health-Insight.git
cd Health-Insight
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

- [ ] **Step 5: Copiar o wallet e o `.env` para a instância**

Do computador local (fora da instância):

```bash
scp -r wallet ubuntu@<IP_PUBLICO>:~/Health-Insight/wallet
scp .env ubuntu@<IP_PUBLICO>:~/Health-Insight/.env
```

- [ ] **Step 6: Escrever `deploy/healthinsight-api.service`**

```ini
[Unit]
Description=HealthInsight FastAPI
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Health-Insight
EnvironmentFile=/home/ubuntu/Health-Insight/.env
ExecStart=/home/ubuntu/Health-Insight/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 7: Escrever `deploy/nginx-healthinsight.conf`**

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 8: Commit dos arquivos de deploy (não do wallet/.env)**

```bash
git add deploy/healthinsight-api.service deploy/nginx-healthinsight.conf
git commit -m "chore: arquivos de configuracao de deploy (systemd + nginx)"
```

---

## Task 17: Deploy — publicar a aplicação

**Files:**
- Nenhum arquivo novo no repositório — task de execução na Compute Instance provisionada na Task 16.

**Interfaces:**
- Consumes: `deploy/healthinsight-api.service`, `deploy/nginx-healthinsight.conf` (Task 16); repositório clonado na instância.
- Produces: URL pública funcionando — é o link exigido na entrega da Sprint 2.

- [ ] **Step 1: Instalar o unit file do systemd**

Na instância, via SSH:

```bash
sudo cp ~/Health-Insight/deploy/healthinsight-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now healthinsight-api
```

- [ ] **Step 2: Verificar que o serviço está rodando**

```bash
sudo systemctl status healthinsight-api
curl http://127.0.0.1:8000/api/health
```

Expected: `active (running)` e `{"status":"ok"}`.

- [ ] **Step 3: Instalar a configuração do nginx**

```bash
sudo cp ~/Health-Insight/deploy/nginx-healthinsight.conf /etc/nginx/sites-available/healthinsight
sudo ln -s /etc/nginx/sites-available/healthinsight /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

- [ ] **Step 4: Verificar o acesso público**

Do computador local (fora da instância):

```bash
curl http://<IP_PUBLICO>/api/health
```

Expected: `{"status":"ok"}`. Depois, abrir `http://<IP_PUBLICO>/` no
navegador e confirmar que o dashboard carrega com dados reais.

- [ ] **Step 5: Registrar a URL pública**

Anotar `http://<IP_PUBLICO>/` — esse é o link a ser incluído no PPTX final
(item "Link da aplicação funcionando", 10% da nota da Sprint 2) e no README
(Task 18).

Nada a commitar nesta task além do que já foi commitado na Task 16.

---

## Task 18: Documentação — README e diagrama de arquitetura

**Files:**
- Modify: `README.md`
- Create: `docs/arquitetura.md`

**Interfaces:**
- Nenhuma — task de documentação, consome o conhecimento de todas as tasks anteriores.

- [ ] **Step 1: Completar o `README.md`**

```markdown
# HealthInsight

Painel analítico sobre dados do SUS (DATASUS/SIH-SUS + CNES), com Oracle
Autonomous Database como core de dados e Oracle Select AI para consultas
em linguagem natural. Projeto do Challenge FIAP/Oracle — Grupo 35.

**Aplicação publicada:** http://<IP_PUBLICO>/

## Estrutura do repositório

- `etl/` — download (DATASUS/CNES via `pysus`), tratamento e carga dos
  dados no Oracle Autonomous Database.
- `sql/` — DDL do schema e configuração do Select AI.
- `notebooks/` — análise exploratória (EDA) e modelo preditivo de
  internações.
- `api/` — backend FastAPI: endpoints REST consumidos pelo dashboard e
  integração com Select AI; também serve o front-end estático
  (`api/static/index.html`).
- `docs/` — spec de arquitetura, plano de implementação e diagrama
  atualizado.

## Rodando localmente

1. `python -m venv .venv && .venv\Scripts\activate` (Windows) ou
   `source .venv/bin/activate` (Linux/Mac)
2. `pip install -r requirements.txt`
3. Copiar `.env.example` para `.env` e preencher com as credenciais do
   Oracle Autonomous Database (ver `docs/superpowers/plans/2026-08-21-healthinsight-mvp.md`,
   Task 1).
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
- Diagrama de arquitetura: `docs/arquitetura.md`
```

- [ ] **Step 2: Escrever `docs/arquitetura.md`**

```markdown
# Arquitetura implementada — HealthInsight

## Fluxo de dados ponta a ponta

1. **Ingestão:** scripts em `etl/download.py` baixam dados públicos do
   SIH-SUS (internações) e do CNES (estabelecimentos) via biblioteca
   `pysus`, diretamente dos servidores do DATASUS.
2. **Tratamento:** `etl/transform.py` normaliza tipos, remove registros
   inválidos e classifica procedimentos por tipo de atendimento
   (clínico/cirúrgico/obstétrico/psiquiátrico/outros) a partir do CID.
3. **Carga:** `etl/load.py` grava os dados tratados em três tabelas do
   Oracle Autonomous Database: `estabelecimentos`, `procedimentos`,
   `internacoes` (schema em `sql/schema.sql`).
4. **Consumo analítico:**
   - Um backend FastAPI (`api/`) expõe endpoints REST que agregam os
     dados sob demanda para os 3 dashboards do front-end.
   - Um perfil Oracle Select AI (`sql/select_ai_setup.sql`) permite
     consultas em linguagem natural diretamente sobre o schema, expostas
     via `POST /api/ai/query`.
5. **Visualização:** o front-end (`api/static/index.html`, HTML/CSS/JS +
   Chart.js) consome os endpoints acima e renderiza os 4 dashboards.
6. **Deploy:** o mesmo processo FastAPI (servindo API + estáticos) roda
   em uma Compute Instance OCI atrás de nginx (`deploy/`), na mesma conta
   do banco.

## Tecnologias por camada

| Camada          | Tecnologia                                   |
|-----------------|-----------------------------------------------|
| Ingestão        | Python, `pysus` (DATASUS/SIH-SUS, CNES)       |
| Tratamento      | pandas                                        |
| Armazenamento   | Oracle Autonomous Database                    |
| IA conversacional | Oracle Select AI (`DBMS_CLOUD_AI`)          |
| Backend         | FastAPI, python-oracledb (thin mode)          |
| Visualização    | HTML/CSS/JS, Chart.js                         |
| Deploy          | OCI Compute Instance, nginx, systemd          |

## O que ainda não foi implementado / próximos passos

- Gráfico "Crescimento por tipo (24 meses)" da tela Análise de Atendimento
  continua com dados de exemplo — endpoint não coberto neste MVP.
- Carga de dados limitada às UFs definidas em `etl/load.py::UFS`; expandir
  para todas as 27 unidades federativas é a evolução natural do pipeline.
- Modelo preditivo do notebook é uma regressão linear simples sobre a
  série mensal; um modelo de série temporal (ex. ARIMA/Prophet) é a
  evolução natural se houver tempo.
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/arquitetura.md
git commit -m "docs: README completo e diagrama de arquitetura implementada"
```

---

## Depois da Task 18

O que resta é fora do escopo de código (spec, seção "Repositório e
documentação"): preencher a planilha
`Informacoes_Finais_Projeto_Integrantes_v1.xlsx`, atualizar a documentação
de gestão de projeto da Sprint 1, montar o PPTX final com prints das telas
funcionando (Tasks 14-15), o link da Task 17, o link do notebook (Task 6) e
gravar o vídeo pitch.
