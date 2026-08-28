from api.routers import capacidade as router_module


def test_ocupacao_estados_endpoint(client, monkeypatch):
    def fake_get_ocupacao_estados(conn, ano):
        return [{"uf": "SP", "taxa_ocupacao": 82.1, "internacoes": 300000}]

    monkeypatch.setattr(router_module.q, "get_ocupacao_estados", fake_get_ocupacao_estados)

    resp = client.get("/api/ocupacao-estados?ano=2024")

    assert resp.status_code == 200
    assert resp.json()[0]["uf"] == "SP"


def test_hospitais_endpoint_aplica_filtros(client, monkeypatch):
    capturado = {}

    def fake_get_hospitais(conn, ano, regiao, tipo):
        capturado["regiao"] = regiao
        capturado["tipo"] = tipo
        return [{
            "nome": "Hospital das Clínicas SP",
            "municipio": "São Paulo",
            "regiao": "Sudeste",
            "internacoes": 42810,
            "permanencia_media": 6.2,
            "taxa_ocupacao": 93.0,
            "status": "critico",
        }]

    monkeypatch.setattr(router_module.q, "get_hospitais", fake_get_hospitais)

    resp = client.get("/api/hospitais?ano=2024&regiao=Sudeste&tipo=Hospital")

    assert resp.status_code == 200
    assert capturado == {"regiao": "Sudeste", "tipo": "Hospital"}
    assert resp.json()[0]["status"] == "critico"
