from unittest.mock import MagicMock
from api.queries.visao_geral import get_kpis


def test_get_kpis_calcula_taxa_ocupacao_por_censo_medio():
    conn = MagicMock()
    cursor = conn.cursor.return_value
    # 1a query: total_internacoes, permanencia_media, soma_dias
    # 2a query: leitos_totais
    cursor.fetchone.side_effect = [
        (1000, 5.0, 5000),  # soma_dias = 5000 dias-paciente na competencia
        (500,),              # 500 leitos totais na rede
    ]

    resultado = get_kpis(conn, 2024)

    # A carga cobre apenas a competencia 2024-01 => divisor DIAS_CARGA_ATUAL = 31.
    # Os leitos do fixture subiram de 100 para 500 porque com 100 leitos o censo
    # medio (161) ultrapassaria a rede inteira e leitos_disponiveis ficaria preso
    # no piso 0, deixando de exercitar a subtracao. Com 500 leitos o cenario e
    # plausivel e as duas contas continuam verificaveis.
    # censo medio diario = 5000 / 31 = 161.29...
    # taxa ocupacao = 161.29... / 500 * 100 = 32.258... -> 32.3%
    # leitos disponiveis = 500 - round(161.29) = 500 - 161 = 339
    assert resultado["total_internacoes"] == 1000
    assert resultado["permanencia_media"] == 5.0
    assert resultado["taxa_ocupacao"] == 32.3
    assert resultado["leitos_disponiveis"] == 339
