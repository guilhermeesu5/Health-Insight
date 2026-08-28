from api.routers import atendimento as router_module


def test_tipos_atendimento_endpoint(client, monkeypatch):
    def fake_get_tipos_atendimento(conn, ano):
        return {
            "distribuicao": [{"tipo": "clinico", "percentual": 38.0}],
            "top_procedimentos": [{
                "codigo": "O80", "nome": "O80", "tipo": "obstetrico",
                "internacoes": 198440, "permanencia_media": 2.1,
            }],
        }

    monkeypatch.setattr(router_module.q, "get_tipos_atendimento", fake_get_tipos_atendimento)

    resp = client.get("/api/tipos-atendimento?ano=2024")

    assert resp.status_code == 200
    body = resp.json()
    assert body["distribuicao"][0]["tipo"] == "clinico"
    assert body["top_procedimentos"][0]["codigo"] == "O80"
