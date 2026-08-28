from unittest.mock import MagicMock
from api.queries.visao_geral import get_kpis


def test_get_kpis_calcula_taxa_ocupacao_por_censo_medio():
    conn = MagicMock()
    cursor = conn.cursor.return_value
    # 1a query: total_internacoes, permanencia_media, soma_dias
    # 2a query: leitos_totais
    cursor.fetchone.side_effect = [
        (1000, 5.0, 5000),  # soma_dias = 5000 dias-paciente no ano
        (100,),              # 100 leitos totais na rede
    ]

    resultado = get_kpis(conn, 2024)

    # censo medio diario = 5000 / 366 (2024 e bissexto) ~= 13.66
    # taxa ocupacao = 13.66 / 100 * 100 ~= 13.7%
    assert resultado["total_internacoes"] == 1000
    assert resultado["permanencia_media"] == 5.0
    assert resultado["taxa_ocupacao"] == 13.7
    assert resultado["leitos_disponiveis"] == 86
