from api.routers import visao_geral as router_module


def test_kpis_endpoint(client, monkeypatch):
    def fake_get_kpis(conn, ano):
        assert ano == 2024
        return {
            "total_internacoes": 1284730,
            "permanencia_media": 5.3,
            "leitos_disponiveis": 48210,
            "taxa_ocupacao": 74.6,
        }

    monkeypatch.setattr(router_module.q, "get_kpis", fake_get_kpis)

    resp = client.get("/api/kpis?ano=2024")

    assert resp.status_code == 200
    assert resp.json()["taxa_ocupacao"] == 74.6


def test_tendencia_mensal_endpoint(client, monkeypatch):
    def fake_get_tendencia_mensal(conn, ano):
        return [{"mes": 1, "total": 98000}, {"mes": 2, "total": 102000}]

    monkeypatch.setattr(router_module.q, "get_tendencia_mensal", fake_get_tendencia_mensal)

    resp = client.get("/api/tendencia-mensal?ano=2024")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_leitos_regiao_endpoint(client, monkeypatch):
    def fake_get_leitos_regiao(conn, ano):
        return [{"regiao": "Sudeste", "ocupados": 18200, "disponiveis": 5800}]

    monkeypatch.setattr(router_module.q, "get_leitos_regiao", fake_get_leitos_regiao)

    resp = client.get("/api/leitos-regiao?ano=2024")

    assert resp.status_code == 200
    assert resp.json()[0]["regiao"] == "Sudeste"
