from fastapi.testclient import TestClient

from blockchain_api.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(difficulty=1))


def test_health_check() -> None:
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_transaction_mining_flow() -> None:
    client = make_client()

    transaction_response = client.post(
        "/api/v1/transactions",
        json={"sender": "alice", "recipient": "bob", "amount": "12.50"},
    )
    assert transaction_response.status_code == 201

    mining_response = client.post("/api/v1/mine/miner-01")
    assert mining_response.status_code == 200
    assert len(mining_response.json()["block"]["transactions"]) == 2

    chain_response = client.get("/api/v1/chain")
    assert chain_response.status_code == 200
    assert chain_response.json()["length"] == 2

    validation_response = client.get("/api/v1/chain/validate")
    assert validation_response.json() == {"valid": True}


def test_rejects_same_sender_and_recipient() -> None:
    response = make_client().post(
        "/api/v1/transactions",
        json={"sender": "alice", "recipient": "alice", "amount": "1"},
    )

    assert response.status_code == 422
