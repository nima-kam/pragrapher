from __future__ import annotations


DEMO_PASSWORD = "ParagrapherDemo123!"


def request(client, method: str, path: str, payload=None, **kwargs):
    method = method.lower()
    headers = dict(kwargs.pop("headers", {}))
    if method not in {"get", "head", "options"}:
        csrf = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
        headers["X-CSRF-Token"] = csrf
    if headers:
        kwargs["headers"] = headers
    if payload is not None:
        kwargs["json"] = payload
    return getattr(client, method)(path, **kwargs)


def sign_in(client, username="nima_reader", password=DEMO_PASSWORD):
    response = request(client, "post", "/api/v1/auth/login", {
        "username": username,
        "password": password,
    })
    assert response.status_code == 200, response.get_json()
    return response.get_json()["data"]["user"]


def seed(client):
    response = client.application.test_cli_runner().invoke(args=["seed-demo"])
    assert response.exit_code == 0, response.output
    return response.output
