def test_health_check_uses_empty_test_database(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status" : "ok", "cards_loaded" :0}