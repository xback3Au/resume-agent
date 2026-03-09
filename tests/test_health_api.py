"""健康检查接口测试。"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    """健康接口应返回 ok。"""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
