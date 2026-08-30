from api.queries.visao_geral import DIAS_CARGA_ATUAL


def get_ocupacao_estados(conn, ano: int) -> list[dict]:
    cur = conn.cursor()

    # leitos_totais é uma dimensão por estabelecimento: agregá-lo no mesmo
    # JOIN com internacoes (tabela fato) repetiria o valor uma vez por
    # internação e inflaria a soma. Agregamos separadamente e combinamos aqui.
    cur.execute("SELECT uf, SUM(leitos_totais) FROM estabelecimentos GROUP BY uf")
    leitos_por_uf = {uf: leitos or 0 for uf, leitos in cur.fetchall()}

    cur.execute(
        """
        SELECT e.uf, SUM(i.dias_permanencia) AS soma_dias, COUNT(i.id) AS internacoes
        FROM estabelecimentos e
        JOIN internacoes i ON i.estabelecimento_id = e.id
        WHERE EXTRACT(YEAR FROM i.data_internacao) = :ano
        GROUP BY e.uf
        """,
        ano=ano,
    )
    resultado = []
    for uf, soma_dias, internacoes in cur.fetchall():
        leitos_totais = leitos_por_uf.get(uf, 0)
        censo_medio = (soma_dias or 0) / DIAS_CARGA_ATUAL
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
    resultado = []
    for nome, municipio, regiao_, leitos_totais, internacoes, permanencia_media, soma_dias in cur.fetchall():
        censo_medio = (soma_dias or 0) / DIAS_CARGA_ATUAL
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
