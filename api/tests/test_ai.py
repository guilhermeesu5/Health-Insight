from api.routers import ai as router_module


def test_ai_query_endpoint(client, monkeypatch):
    def fake_perguntar(conn, pergunta):
        assert pergunta == "Qual região teve maior crescimento?"
        return {"resposta": "A região Norte cresceu 14,2%.", "dados": "[]"}

    monkeypatch.setattr(router_module.q, "perguntar", fake_perguntar)

    resp = client.post("/api/ai/query", json={"pergunta": "Qual região teve maior crescimento?"})

    assert resp.status_code == 200
    assert "Norte" in resp.json()["resposta"]


def test_ai_query_endpoint_rejeita_pergunta_vazia(client):
    resp = client.post("/api/ai/query", json={"pergunta": ""})

    assert resp.status_code == 422
