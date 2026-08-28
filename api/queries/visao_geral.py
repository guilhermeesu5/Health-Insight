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
