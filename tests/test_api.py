from decimal import Decimal

from fastapi.testclient import TestClient

from blockchain_api.core.crypto import generate_wallet, sign_transaction
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
    alice = generate_wallet()

    reward_response = client.post(f"/api/v1/mine/{alice['address']}")
    assert reward_response.status_code == 200

    signature = sign_transaction(
        private_key=alice["private_key"],
        sender=alice["address"],
        recipient="bob",
        amount=Decimal("0.50"),
        nonce=0,
    )

    transaction_response = client.post(
        "/api/v1/transactions",
        json={
            "sender": alice["address"],
            "recipient": "bob",
            "amount": "0.50",
            "nonce": 0,
            "public_key": alice["public_key"],
            "signature": signature,
        },
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

    wallet_response = client.get(f"/api/v1/wallets/{alice['address']}/balance")
    assert wallet_response.status_code == 200
    assert wallet_response.json()["confirmed"] == "0.50"


def test_rejects_transaction_with_insufficient_funds() -> None:
    client = make_client()
    alice = generate_wallet()
    signature = sign_transaction(
        private_key=alice["private_key"],
        sender=alice["address"],
        recipient="bob",
        amount=Decimal("1"),
        nonce=0,
    )
    response = client.post(
        "/api/v1/transactions",
        json={
            "sender": alice["address"],
            "recipient": "bob",
            "amount": "1",
            "nonce": 0,
            "public_key": alice["public_key"],
            "signature": signature,
        },
    )

    assert response.status_code == 409


def test_rejects_same_sender_and_recipient() -> None:
    wallet = generate_wallet()
    response = make_client().post(
        "/api/v1/transactions",
        json={
            "sender": wallet["address"],
            "recipient": wallet["address"],
            "amount": "1",
            "nonce": 0,
            "public_key": wallet["public_key"],
            "signature": "x" * 88,
        },
    )

    assert response.status_code == 422


def test_generates_cryptographic_wallet() -> None:
    response = make_client().post("/api/v1/wallets/generate")

    assert response.status_code == 200
    assert len(response.json()["address"]) == 40
    assert response.json()["public_key"]
    assert response.json()["private_key"]


def test_registers_nodes_and_reports_status() -> None:
    client = make_client()

    register = client.post(
        "/api/v1/nodes/register",
        json={"urls": ["http://node2:8000/"]},
    )
    status = client.get("/api/v1/nodes")

    assert register.status_code == 200
    assert status.json()["node_id"]
    assert status.json()["peers"] == ["http://node2:8000"]


def test_websocket_receives_new_block_event() -> None:
    client = make_client()

    with client.websocket_connect("/ws/blocks") as websocket:
        snapshot = websocket.receive_json()
        response = client.post("/api/v1/mine/realtime-miner")
        event = websocket.receive_json()

    assert snapshot == {"type": "chain_snapshot", "length": 1, "valid": True}
    assert response.status_code == 200
    assert event["type"] == "block_mined"
    assert event["block"]["index"] == 1
