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
