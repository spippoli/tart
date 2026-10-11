from fastapi.testclient import TestClient

from tart.api.app import create_app


def test_health_answers_ok_when_the_api_is_up() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.text == "ok"
