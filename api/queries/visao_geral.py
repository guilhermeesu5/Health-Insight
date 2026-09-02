# A carga atual do ETL cobre apenas a competência 2026-05 (ver
# etl/load.py: ANO, MES = 2026, 5) — um único mês de 31 dias — não o
# ano inteiro. Ajustar esta constante (ou torná-la dependente de mes)
# se mais competências forem carregadas no futuro.
DIAS_CARGA_ATUAL = 31


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

    # Censo médio diário = dias-paciente no período / dias de calendário —
    # estimativa padrão de ocupação média a partir de dados de admissão.
    censo_medio_diario = soma_dias / DIAS_CARGA_ATUAL
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


def get_tendencia_diaria(conn, ano: int, mes: int) -> list[dict]:
    # A carga atual cobre um único mês (ver DIAS_CARGA_ATUAL acima), então
    # uma tendência dia-a-dia dentro desse mês é mais honesta com os dados
    # reais disponíveis do que uma série "mensal" com um ponto só.
    cur = conn.cursor()
    cur.execute(
        """
        SELECT EXTRACT(DAY FROM data_internacao) AS dia, COUNT(*) AS total
        FROM internacoes
        WHERE EXTRACT(YEAR FROM data_internacao) = :ano
          AND EXTRACT(MONTH FROM data_internacao) = :mes
        GROUP BY EXTRACT(DAY FROM data_internacao)
        ORDER BY dia
        """,
        ano=ano,
        mes=mes,
    )
    return [{"dia": int(dia), "total": total} for dia, total in cur.fetchall()]


def get_leitos_regiao(conn, ano: int) -> list[dict]:
    cur = conn.cursor()

    # leitos_totais é uma dimensão por estabelecimento: agregá-lo no mesmo
    # JOIN com internacoes (tabela fato) repetiria o valor uma vez por
    # internação e inflaria a soma. Agregamos separadamente e combinamos aqui.
    cur.execute("SELECT regiao, SUM(leitos_totais) FROM estabelecimentos GROUP BY regiao")
    leitos_por_regiao = {regiao: leitos or 0 for regiao, leitos in cur.fetchall()}

    cur.execute(
        """
        SELECT e.regiao, SUM(i.dias_permanencia) AS soma_dias
        FROM estabelecimentos e
        JOIN internacoes i ON i.estabelecimento_id = e.id
        WHERE EXTRACT(YEAR FROM i.data_internacao) = :ano
        GROUP BY e.regiao
        """,
        ano=ano,
    )
    resultado = []
    for regiao, soma_dias in cur.fetchall():
        ocupados = round((soma_dias or 0) / DIAS_CARGA_ATUAL)
        leitos_totais = leitos_por_regiao.get(regiao, 0)
        resultado.append({
            "regiao": regiao,
            "ocupados": ocupados,
            "disponiveis": max(int(leitos_totais) - ocupados, 0),
        })
    return resultado
