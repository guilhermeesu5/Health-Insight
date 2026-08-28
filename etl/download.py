import pandas as pd
import pysus


def baixar_sih(uf: str, ano: int, mes: int) -> pd.DataFrame:
    """Baixa internações do SIH-SUS (grupo RD - Reduzida) para uma UF/mês."""
    df = pysus.sih(uf.upper(), ano, mes, group="RD", as_dataframe=True, show_progress=False)
    return pd.DataFrame({
        "data_internacao": df["DT_INTER"],
        "codigo_cnes": df["CNES"],
        "codigo_procedimento": df["DIAG_PRINC"],
        "dias_permanencia": df["DIAS_PERM"],
        "valor_total": df.get("VAL_TOT"),
    })


def baixar_cnes(uf: str, ano: int, mes: int) -> pd.DataFrame:
    """Baixa o cadastro de estabelecimentos (CNES) para uma UF/mês.

    A camada "ST" do CNES não traz nome de estabelecimento nem nome de
    município (só códigos) — usamos um nome legível a partir do próprio
    código CNES como placeholder honesto, e o código de município cru.
    Ver docs/arquitetura.md (Task 18) para a limitação documentada.
    """
    df = pysus.cnes(uf.upper(), ano, mes, group="ST", as_dataframe=True, show_progress=False)

    colunas_leitos = [c for c in df.columns if c.startswith("QTLEIT")]
    leitos_totais = df[colunas_leitos].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)

    return pd.DataFrame({
        "codigo_cnes": df["CNES"],
        "nome": df["CNES"].apply(lambda c: f"Estabelecimento CNES {c}"),
        "municipio": df["CODUFMUN"].astype(str),
        "uf": uf.upper(),
        "tipo": df["TP_UNID"],
        "natureza": df["NAT_JUR"],
        "leitos_totais": leitos_totais,
    })
