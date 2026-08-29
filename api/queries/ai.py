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
