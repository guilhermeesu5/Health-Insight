from dotenv import load_dotenv
load_dotenv()

import os
import oracledb
import pandas as pd

from etl.download import baixar_sih, baixar_cnes
from etl.transform import limpar_internacoes, regiao_da_uf, classificar_tipo_procedimento

UFS = ["AC", "DF", "CE", "SC", "AM"]
ANO, MES = 2026, 5


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
