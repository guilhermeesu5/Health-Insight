# HealthInsight Oracle — MVP funcional (Sprint 2)

**Data:** 2026-08-21
**Status:** Aprovado para planejamento
**Entrega alvo:** Sprint 2 do Challenge FIAP/Oracle — prazo 01/09/2026

## Contexto

O grupo (HealthInsight, Grupo 35) entregou na Sprint 1 uma proposta em PDF
descrevendo um painel analítico sobre dados do SUS (DATASUS/SIH-SUS + CNES),
com Oracle Autonomous Database como core e Oracle Select AI permitindo
consultas em linguagem natural. Também existe um protótipo de front-end
(`index.html`) com 4 telas (Visão Geral, Capacidade Hospitalar, Análise de
Atendimento, Oracle Select AI), construído em HTML/CSS/JS + Chart.js.

Hoje esse front-end é **100% mockup**: todos os dados dos gráficos e tabelas
estão hardcoded em JavaScript, e a tela "Oracle Select AI" é uma função de
keyword-matching que devolve textos pré-escritos — não há banco, não há
backend, não há IA real por trás.

A Sprint 2 exige entregar um **MVP de fato funcionando**, com arquitetura
implementada (não só planejada), evidências de código, modelos analíticos
reais e um link de aplicação acessível e navegável.

## Objetivo

Transformar o mockup existente em uma aplicação real: dados verídicos do
DATASUS armazenados em um Oracle Autonomous Database, um backend que serve
esses dados ao front-end existente, e uma integração real de Oracle Select AI
para a tela de perguntas em linguagem natural — tudo publicado com um link
acessível, hospedado na própria OCI.

## Decisões já tomadas (não reabrir sem justificativa)

- **Infra de banco:** Oracle Autonomous Database (conta OCI sendo
  providenciada pelo usuário).
- **Fonte de dados:** dados reais baixados do DATASUS/TabNet (SIH-SUS), e/ou
  CNES para dados de estabelecimentos.
- **Integração front↔dados:** API própria em Python (FastAPI); o
  `index.html` existente é adaptado para consumir essa API via `fetch()`, em
  vez de reescrever a aplicação em Oracle APEX.
- **Deploy:** uma Compute Instance na própria OCI, hospedando a API e os
  arquivos estáticos juntos (mesmo processo), gerando o link exigido na
  entrega.
- **Profundidade analítica:** EDA documentada + um modelo preditivo simples
  e explicável (ex.: regressão ou média móvel/ARIMA leve) prevendo
  volume de internações ou taxa de ocupação por região.

## Arquitetura

```
DATASUS/TabNet (CSV) → ETL (Python/oracledb) → Oracle Autonomous Database
                                                        │
                                                        ├── Select AI (NL→SQL)
                                                        │
                                                  FastAPI (backend)
                                             ├── serve estáticos (index.html)
                                             ├── endpoints JSON por dashboard
                                             └── endpoint /api/ai/query
                                                        │
                                        Front-end (index.html adaptado)
                                                        │
                                Deploy: Compute Instance única na OCI
```

Um único processo FastAPI serve tanto os arquivos estáticos quanto a API —
evita CORS e um segundo servidor, reduzindo superfície de deploy dado o
prazo curto.

## Componentes

### 1. Banco de dados (Oracle Autonomous Database)

Schema mínimo, suficiente para recalcular os KPIs e gráficos já existentes
no mockup:

- **`estabelecimentos`** — hospital/UBS/UPA: nome, município, região, tipo,
  natureza (público/privado/filantrópico). Fonte: CNES.
- **`procedimentos`** — dimensão: código (CID/procedimento SIH), nome, tipo
  (clínico/cirúrgico/obstétrico/psiquiátrico/outros).
- **`internacoes`** — fato: data de internação, `estabelecimento_id`,
  `procedimento_id`, dias de permanência, valor (se disponível). Fonte:
  SIH-SUS.

Índices em `data_internacao`, `estabelecimento_id` e `procedimento_id` para
as agregações usadas nos dashboards (mensal, por região, por tipo).

### 2. ETL

Scripts Python (`/etl`) que:
1. Baixam os arquivos CSV/DBC do SIH-SUS via TabNet (período recente
   disponível — a confirmar qual ano tem dado completo) e do CNES para
   estabelecimentos.
2. Tratam: tipagem, nulos, normalização de nomes de município/UF, join
   SIH↔CNES por código do estabelecimento.
3. Carregam nas 3 tabelas acima via `oracledb` (driver Python para Oracle).

Esses mesmos scripts/dados tratados alimentam o notebook de EDA.

### 3. Analytics (notebook)

Notebook Jupyter (`/notebooks`) com:
- EDA: distribuições, sazonalidade mensal, outliers de permanência/ocupação.
- Um modelo preditivo simples (regressão linear ou média móvel/ARIMA leve)
  prevendo volume de internações ou taxa de ocupação por região para o
  próximo período, com explicação da técnica e das métricas de avaliação.

Os gráficos/outputs desse notebook viram evidência visual no PPT e no
repositório técnico.

### 4. Backend (FastAPI)

Endpoints REST (`/api`) substituindo os arrays fixos do JS atual:

- `GET /api/kpis` — total internações, permanência média, leitos
  disponíveis, taxa de ocupação (tela Visão Geral).
- `GET /api/tendencia-mensal` — série mensal de internações (ano atual vs.
  anterior).
- `GET /api/ocupacao-estados` — taxa de ocupação por UF (mapa do Brasil).
- `GET /api/leitos-regiao` — ocupados vs. disponíveis por região.
- `GET /api/hospitais` — tabela de estabelecimentos com métricas de
  ocupação (tela Capacidade Hospitalar), com filtros de tipo/região/período.
- `GET /api/tipos-atendimento` — distribuição percentual por tipo (tela
  Análise de Atendimento) + top procedimentos.
- `POST /api/ai/query` — recebe a pergunta em português, aciona o Select AI
  configurado no Autonomous Database, devolve texto de resposta + dados
  estruturados para atualizar o gráfico da tela Oracle Select AI.

### 5. Select AI

Configurado diretamente no Oracle Autonomous Database (perfil Select AI
com um provider de LLM disponível na OCI), apontando para o schema das 3
tabelas acima. O endpoint `/api/ai/query` chama esse perfil via
`DBMS_CLOUD_AI` (ou equivalente), recebe SQL gerado + resultado, e formata
a resposta para o front-end. Substitui completamente a função
`getKey()`/`aiAnswers{}` hardcoded que existe hoje no `index.html`.

### 6. Front-end

O `index.html` existente é preservado (design, CSS, layout, Chart.js) —
alteração cirúrgica: trocar os blocos que hoje inicializam os gráficos com
arrays fixos por chamadas `fetch()` aos endpoints acima, e trocar
`runAI()`/`getKey()` por uma chamada real a `POST /api/ai/query`.

### 7. Deploy

Uma Compute Instance (ou Container Instance) na mesma conta OCI do banco,
rodando o FastAPI via uvicorn atrás de nginx. Gera o link de "aplicação
funcionando" exigido pela avaliação da Sprint 2.

### 8. Repositório e documentação

Estrutura de pasta sugerida:

```
/etl          — scripts de download/tratamento/carga
/notebooks    — EDA + modelo preditivo
/api          — FastAPI (backend + serve do index.html)
/docs         — arquitetura atualizada, gestão de projeto atualizada
README.md
```

Documentos a atualizar/gerar para a entrega (fora do código):
- Planilha `Informacoes_Finais_Projeto_Integrantes_v1.xlsx` preenchida.
- Documentação de gestão de projeto da Sprint 1, atualizada.
- Diagrama de arquitetura atualizado refletindo o que foi **de fato**
  implementado (vs. planejado).
- PPTX final (`EC_Sprint_2_1TSCO_EvidenciasConstrucao_...pptx`) com prints,
  descrição do escopo entregue, link do vídeo pitch e link da aplicação.

## Fora de escopo (YAGNI)

- Autenticação/autorização de usuários — não pedido na entrega, não
  necessário para demo.
- Ingestão em tempo real/streaming — dados SIH-SUS são batch por natureza;
  carga periódica simples é suficiente.
- Multi-tenant, alta disponibilidade, CI/CD — desnecessário para um MVP de
  demo acadêmico.
- Reescrever a aplicação em Oracle APEX — decisão já tomada de manter o
  HTML existente.

## Riscos conhecidos

- **Prazo de acesso à conta OCI**: se a criação/liberação da conta Oracle
  Cloud atrasar, toda a cadeia (banco → Select AI → API → deploy) fica
  bloqueada. Mitigar priorizando esse setup como primeiro passo do plano.
- **Disponibilidade de dados SIH-SUS recentes**: pode não haver dados
  completos para o ano corrente no TabNet; validar qual período usar antes
  de fixar os gráficos de "tendência mensal".
- **Configuração do Select AI**: é a peça mais nova/desconhecida da stack;
  reservar tempo de troubleshooting específico para ela.

## Critérios de sucesso

- Os 4 dashboards do `index.html` exibem dados reais vindos do Oracle
  Autonomous Database (não mais arrays hardcoded).
- A tela "Oracle Select AI" responde perguntas em linguagem natural via
  Select AI real, não mais por keyword-matching.
- Existe um link público (hospedado na OCI) navegável para a apresentação
  e para a banca avaliadora.
- Repositório técnico organizado (ETL, notebook, API, docs) publicável no
  GitHub.
- Notebook com EDA e um modelo preditivo simples, com evidências visuais.
