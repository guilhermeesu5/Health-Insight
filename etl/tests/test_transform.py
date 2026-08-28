import pandas as pd
import pytest
from etl.transform import regiao_da_uf, classificar_tipo_procedimento, limpar_internacoes


def test_regiao_da_uf_conhecida():
    assert regiao_da_uf("SP") == "Sudeste"
    assert regiao_da_uf("am") == "Norte"


def test_regiao_da_uf_desconhecida_levanta_erro():
    with pytest.raises(ValueError):
        regiao_da_uf("XX")


def test_classificar_tipo_procedimento():
    assert classificar_tipo_procedimento("O80") == "obstetrico"
    assert classificar_tipo_procedimento("K37") == "cirurgico"
    assert classificar_tipo_procedimento("J18") == "clinico"
    assert classificar_tipo_procedimento("F20") == "psiquiatrico"
    assert classificar_tipo_procedimento("Z99") == "outros"


def test_limpar_internacoes_remove_linhas_invalidas():
    df = pd.DataFrame({
        "data_internacao": ["2024-01-15", None, "2024-02-01", "data-invalida"],
        "codigo_cnes": ["123", "456", None, "789"],
        "codigo_procedimento": ["O80", "K37", "J18", "I50"],
        "dias_permanencia": [3, 5, 2, -1],
    })

    resultado = limpar_internacoes(df)

    assert len(resultado) == 1
    assert resultado.iloc[0]["codigo_cnes"] == "123"


def test_limpar_internacoes_normaliza_tipos():
    df = pd.DataFrame({
        "data_internacao": ["2024-01-15"],
        "codigo_cnes": [" 123 "],
        "codigo_procedimento": [" o80 "],
        "dias_permanencia": ["3"],
    })

    resultado = limpar_internacoes(df)

    assert resultado.iloc[0]["codigo_cnes"] == "123"
    assert resultado.iloc[0]["codigo_procedimento"] == "O80"
    assert resultado.iloc[0]["dias_permanencia"] == 3
    assert isinstance(resultado.iloc[0]["data_internacao"], pd.Timestamp)
