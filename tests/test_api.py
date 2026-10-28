from fastapi.testclient import TestClient

from blockchain_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(difficulty=1))


def test_health_check() -> None:
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_and_static_assets_are_served() -> None:
    client = make_client()

    dashboard = client.get("/")
    stylesheet = client.get("/static/app.css")

    assert dashboard.status_code == 200
    assert "ChainLab" in dashboard.text
    assert stylesheet.status_code == 200
    assert "--cyan" in stylesheet.text


def test_transaction_mining_flow() -> None:
    client = make_client()

    reward_response = client.post("/api/v1/mine/alice")
    assert reward_response.status_code == 200

    transaction_response = client.post(
        "/api/v1/transactions",
        json={"sender": "alice", "recipient": "bob", "amount": "0.50"},
    )
    assert transaction_response.status_code == 201

    mining_response = client.post("/api/v1/mine/miner-01")
    assert mining_response.status_code == 200
    assert len(mining_response.json()["block"]["transactions"]) == 2

    chain_response = client.get("/api/v1/chain")
    assert chain_response.status_code == 200
    assert chain_response.json()["length"] == 3

    validation_response = client.get("/api/v1/chain/validate")
    assert validation_response.json() == {"valid": True}

    wallet_response = client.get("/api/v1/wallets/alice/balance")
    assert wallet_response.status_code == 200
    assert wallet_response.json()["confirmed"] == "0.50"


def test_rejects_transaction_with_insufficient_funds() -> None:
    response = make_client().post(
        "/api/v1/transactions",
        json={"sender": "alice", "recipient": "bob", "amount": "1"},
    )

    assert response.status_code == 409


def test_rejects_same_sender_and_recipient() -> None:
    response = make_client().post(
        "/api/v1/transactions",
        json={"sender": "alice", "recipient": "alice", "amount": "1"},
    )

    assert response.status_code == 422
