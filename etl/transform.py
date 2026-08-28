import pandas as pd

REGIAO_POR_UF = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

# Primeira letra do CID-10 -> tipo de atendimento (classificação usada nas
# telas "Análise de Atendimento" do dashboard).
PREFIXO_CID_PARA_TIPO = {
    "O": "obstetrico",   # gravidez, parto e puerpério
    "K": "cirurgico",    # aparelho digestivo — maioria dos procedimentos cirúrgicos comuns
    "J": "clinico",      # aparelho respiratório
    "I": "clinico",      # aparelho circulatório
    "F": "psiquiatrico", # transtornos mentais
}


def regiao_da_uf(uf: str) -> str:
    uf = (uf or "").strip().upper()
    if uf not in REGIAO_POR_UF:
        raise ValueError(f"UF desconhecida: {uf!r}")
    return REGIAO_POR_UF[uf]


def classificar_tipo_procedimento(codigo_cid: str) -> str:
    prefixo = (codigo_cid or "").strip().upper()[:1]
    return PREFIXO_CID_PARA_TIPO.get(prefixo, "outros")


def limpar_internacoes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df = df.dropna(subset=["data_internacao", "codigo_cnes", "codigo_procedimento", "dias_permanencia"])

    df["data_internacao"] = pd.to_datetime(df["data_internacao"], errors="coerce")
    df = df.dropna(subset=["data_internacao"])

    df["dias_permanencia"] = pd.to_numeric(df["dias_permanencia"], errors="coerce")
    df = df.dropna(subset=["dias_permanencia"])
    df = df[df["dias_permanencia"] >= 0]

    df["codigo_cnes"] = df["codigo_cnes"].astype(str).str.strip()
    df["codigo_procedimento"] = df["codigo_procedimento"].astype(str).str.strip().str.upper()

    return df.reset_index(drop=True)
