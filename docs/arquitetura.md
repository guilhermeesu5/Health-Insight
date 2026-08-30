# Arquitetura implementada — HealthInsight

**Aplicação publicada:** http://64.181.175.100/ — dashboard completo
(`GET /`), endpoints de KPIs/dashboards (ex. `GET /api/kpis?ano=2024`) e
consulta em linguagem natural via Select AI (`POST /api/ai/query`) estão
todos no ar.

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
     dados sob demanda para os dashboards do front-end.
   - Um perfil Oracle Select AI (`sql/select_ai_setup.sql`) permite
     consultas em linguagem natural diretamente sobre o schema, expostas
     via `POST /api/ai/query`. Além do SQL de configuração do perfil, a
     integração exigiu setup de IAM na OCI (dynamic group + policy para
     autenticação via resource principal), fora do escopo puramente de
     banco de dados.
5. **Visualização:** o front-end (`api/static/index.html`, HTML/CSS/JS +
   Chart.js) consome os endpoints acima e renderiza os dashboards.
6. **Deploy:** o mesmo processo FastAPI (servindo API + estáticos) roda
   em uma Compute Instance OCI atrás de nginx (`deploy/`), na mesma conta
   do banco.

## Tecnologias por camada

| Camada             | Tecnologia                                     |
|---------------------|-------------------------------------------------|
| Ingestão            | Python, `pysus` (DATASUS/SIH-SUS, CNES)          |
| Tratamento          | pandas                                           |
| Armazenamento       | Oracle Autonomous Database                       |
| IA conversacional   | Oracle Select AI (`DBMS_CLOUD_AI`) + OCI IAM (dynamic group/policy) |
| Backend             | FastAPI, python-oracledb (thin mode)             |
| Visualização        | HTML/CSS/JS, Chart.js                            |
| Deploy              | OCI Compute Instance (VM.Standard.E2.1.Micro, Always Free, Oracle Linux 9, região sa-saopaulo-1), systemd (`healthinsight-api.service`) + nginx (proxy reverso porta 80 → uvicorn em 127.0.0.1:8000) |

## Escopo dos dados carregados

A carga atual cobre **5 UFs (AC, DF, CE, SC, AM)**, competência
**2024-01** (um único mês) — não é uma carga nacional. Volumes reais:

| Tabela            | Linhas   |
|-------------------|----------|
| `internacoes`     | 135.507  |
| `estabelecimentos`| 48.328   |
| `procedimentos`   | 4.707    |

## O que ainda não foi implementado / próximos passos

1. **Nomes de estabelecimentos são um placeholder**
   (`"Estabelecimento CNES {codigo}"`) — o layout público do CNES (grupo
   "ST") usado no ETL não traz nome de fantasia nem nome de município, só
   códigos; o campo `municipio` mostra o código IBGE cru (ex: "230440"),
   não o nome da cidade. Uma evolução futura precisaria de uma fonte
   complementar para resolver nomes reais.
2. **Gráfico "Crescimento por tipo (24 meses)"** na tela Análise de
   Atendimento continua com dados de exemplo — não há endpoint real para
   ele neste MVP, já que só há 1 mês de dados carregados e uma série de
   24 meses não faria sentido ainda.
3. **Cobertura de dados limitada a 5 UFs e 1 mês** (AC, DF, CE, SC, AM;
   2024-01), não o Brasil inteiro — escolha deliberada para viabilizar o
   prazo da Sprint 2. `etl/load.py` já está pronto para cobrir mais
   UFs/meses, bastando reexecutar com uma lista maior (`UFS` em
   `etl/load.py`).
4. **Sem proteção contra duplicação em recarga:** `carregar_internacoes()`
   (em `etl/load.py`) não impede duplicação de registros se o script for
   reexecutado para uma UF já carregada — hoje funciona porque a carga
   foi feita uma única vez. Uma evolução futura precisaria de um
   delete-before-insert por UF ou de uma constraint de unicidade antes de
   qualquer nova carga.
5. **Modelo preditivo simples:** o notebook usa uma regressão linear
   simples sobre uma série com poucos pontos reais de variação mensal —
   a maioria dos dados reais tem data de admissão histórica de anos
   anteriores à competência carregada, um artefato real dos dados do
   SIH-SUS para internações de longa permanência. Evoluções futuras
   (mais meses de dados, um modelo de série temporal mais robusto)
   melhorariam a qualidade da previsão.
6. **Taxa de ocupação acima de 100% em alguns hospitais:** a ocupação é
   estimada por censo médio diário (dias-paciente ÷ dias do período, com
   `DIAS_CARGA_ATUAL = 31` em `api/queries/visao_geral.py`, pois só a
   competência 2024-01 foi carregada). O denominador de leitos vem do
   CNES, que subnotifica leitos: 44.611 dos 48.328 estabelecimentos
   carregados têm `leitos_totais` 0 ou nulo, e alguns hospitais com
   poucos leitos registrados concentram muitos dias-paciente (ex: CNES
   2480026, 7 leitos e 2.617 dias-paciente em janeiro/2024 → 1.206%).
   São 12 de 508 hospitais acima de 100%; a mediana fica em 12,7%. Os
   valores são exibidos como calculados, sem truncamento — corrigir
   exigiria uma fonte de leitos melhor que o layout público do CNES.
