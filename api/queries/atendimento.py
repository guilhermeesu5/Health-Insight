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
