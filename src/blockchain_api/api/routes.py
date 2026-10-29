"""Rotas versionadas da API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from blockchain_api.api.realtime import RealtimeManager
from blockchain_api.api.schemas import (
    BatchCreate,
    CompanyCreate,
    MessageResponse,
    PeerRegistration,
    ProductCreate,
    TraceEventCreate,
    TransactionCreate,
)
from blockchain_api.core.blockchain import (
    Blockchain,
    InsufficientFundsError,
    InvalidTransactionError,
)
from blockchain_api.core.crypto import generate_wallet
from blockchain_api.core.network import NodeManager
from blockchain_api.core.traceability import TraceabilityError, TraceabilityService

router = APIRouter(prefix="/api/v1")


def get_blockchain(request: Request) -> Blockchain:
    return request.app.state.blockchain


BlockchainDependency = Annotated[Blockchain, Depends(get_blockchain)]


def get_node_manager(request: Request) -> NodeManager:
    return request.app.state.node_manager


def get_realtime_manager(request: Request) -> RealtimeManager:
    return request.app.state.realtime


def get_traceability(request: Request) -> TraceabilityService:
    return request.app.state.traceability


NodeManagerDependency = Annotated[NodeManager, Depends(get_node_manager)]
RealtimeDependency = Annotated[RealtimeManager, Depends(get_realtime_manager)]
TraceabilityDependency = Annotated[TraceabilityService, Depends(get_traceability)]


def require_node_signature(
    request: Request,
    nodes: NodeManagerDependency,
) -> None:
    if not nodes.verify_signature(
        node_id=request.headers.get("X-Node-ID"),
        timestamp=request.headers.get("X-Node-Timestamp"),
        signature=request.headers.get("X-Node-Signature"),
        method=request.method,
        path=request.url.path,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="assinatura do nó ausente, inválida ou expirada",
        )


def serialize_wallet(wallet: dict[str, object]) -> dict[str, object]:
    return {
        key: str(value) if key in {"confirmed", "available", "pending_outgoing"} else value
        for key, value in wallet.items()
    }


@router.get("/chain", summary="Retorna todos os blocos")
def get_chain(blockchain: BlockchainDependency) -> dict[str, object]:
    chain = blockchain.chain
    return {"length": len(chain), "chain": [block.to_dict() for block in chain]}


@router.get("/chain/validate", summary="Verifica a integridade da cadeia")
def validate_chain(blockchain: BlockchainDependency) -> dict[str, bool]:
    return {"valid": blockchain.is_valid()}


@router.get("/transactions/pending", summary="Lista transações ainda não mineradas")
def get_pending_transactions(
    blockchain: BlockchainDependency,
) -> dict[str, object]:
    transactions = blockchain.pending_transactions
    return {
        "count": len(transactions),
        "transactions": [transaction.to_dict() for transaction in transactions],
    }


@router.post(
    "/transactions",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona uma transação ao próximo bloco",
)
async def create_transaction(
    payload: TransactionCreate,
    blockchain: BlockchainDependency,
    realtime: RealtimeDependency,
) -> MessageResponse:
    try:
        transaction = blockchain.add_transaction(
            sender=payload.sender,
            recipient=payload.recipient,
            amount=payload.amount,
            nonce=payload.nonce,
            public_key=payload.public_key,
            signature=payload.signature,
        )
    except InsufficientFundsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidTransactionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    data = transaction.to_dict()
    await realtime.broadcast({"type": "pending_transaction", "data": data})
    return MessageResponse(message="Transação adicionada", data=data)


@router.post("/mine/{miner}", summary="Minera as transações pendentes")
async def mine_block(
    miner: str,
    blockchain: BlockchainDependency,
    realtime: RealtimeDependency,
) -> dict[str, object]:
    try:
        block = blockchain.mine_pending_transactions(miner)
    except InvalidTransactionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    data = block.to_dict()
    await realtime.broadcast({"type": "block_mined", "block": data})
    return {"message": "Bloco minerado", "block": data}


@router.get("/wallets", summary="Lista carteiras e saldos conhecidos")
def list_wallets(blockchain: BlockchainDependency) -> dict[str, object]:
    wallets = blockchain.list_wallets()
    return {"count": len(wallets), "wallets": [serialize_wallet(wallet) for wallet in wallets]}


@router.post("/wallets/generate", summary="Gera um novo par de chaves Ed25519")
def create_wallet() -> dict[str, str]:
    wallet = generate_wallet()
    return {
        **wallet,
        "warning": "A chave privada é exibida apenas nesta resposta; guarde-a com segurança.",
    }


@router.get("/wallets/{address}/balance", summary="Consulta o saldo de uma carteira")
def get_wallet_balance(address: str, blockchain: BlockchainDependency) -> dict[str, object]:
    try:
        balance = blockchain.get_balance(address)
    except InvalidTransactionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return serialize_wallet({"address": address, **balance})


@router.post("/traceability/companies", status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate, traceability: TraceabilityDependency
) -> dict[str, object]:
    try:
        return traceability.create_company(payload.name, payload.document)
    except (TraceabilityError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/traceability/products", status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate, traceability: TraceabilityDependency
) -> dict[str, object]:
    try:
        return traceability.create_product(payload.company_id, payload.code, payload.name)
    except (TraceabilityError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/traceability/batches", status_code=status.HTTP_201_CREATED)
def create_batch(payload: BatchCreate, traceability: TraceabilityDependency) -> dict[str, object]:
    try:
        return traceability.create_batch(payload.product_code, payload.code)
    except (TraceabilityError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/traceability/batches/{batch_code}/events", status_code=status.HTTP_201_CREATED)
async def register_trace_event(
    batch_code: str,
    payload: TraceEventCreate,
    blockchain: BlockchainDependency,
    traceability: TraceabilityDependency,
    realtime: RealtimeDependency,
) -> dict[str, object]:
    try:
        event = traceability.register_event(
            batch_code=batch_code,
            event_type=payload.event_type,
            location=payload.location,
            details=payload.details,
            blockchain=blockchain,
        )
    except (TraceabilityError, InvalidTransactionError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    await realtime.broadcast({"type": "trace_event_anchored", "event": event})
    return event


@router.get("/traceability/public/{batch_code}")
def get_public_batch(batch_code: str, traceability: TraceabilityDependency) -> dict[str, object]:
    batch = traceability.get_public_batch(batch_code)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lote não encontrado")
    return batch


@router.get("/nodes", summary="Retorna a identidade e os peers do nó")
def get_nodes(
    nodes: NodeManagerDependency,
    realtime: RealtimeDependency,
) -> dict[str, object]:
    return {
        "node_id": nodes.node_id,
        "peers": nodes.peers,
        "peer_count": len(nodes.peers),
        "websocket_clients": realtime.connection_count,
        "authentication_enabled": nodes.authentication_enabled,
        "node_url": nodes.node_url,
    }


@router.get(
    "/nodes/chain",
    summary="Retorna a cadeia para um peer autenticado",
    dependencies=[Depends(require_node_signature)],
)
def get_node_chain(blockchain: BlockchainDependency) -> dict[str, object]:
    chain = blockchain.chain
    return {"length": len(chain), "chain": [block.to_dict() for block in chain]}


@router.get(
    "/nodes/peers",
    summary="Retorna peers para descoberta autenticada",
    dependencies=[Depends(require_node_signature)],
)
def get_node_peers(nodes: NodeManagerDependency) -> dict[str, object]:
    advertised = [*nodes.peers]
    if nodes.node_url:
        advertised.append(nodes.node_url)
    return {"node_id": nodes.node_id, "peers": sorted(set(advertised))}


@router.post("/nodes/register", summary="Registra peers HTTP")
def register_nodes(
    payload: PeerRegistration,
    nodes: NodeManagerDependency,
) -> dict[str, object]:
    try:
        peers = nodes.register(payload.urls)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return {"message": "Peers registrados", "peers": peers, "count": len(peers)}


@router.post("/nodes/discover", summary="Descobre peers anunciados pela rede")
async def discover_nodes(nodes: NodeManagerDependency) -> dict[str, object]:
    return await nodes.discover_peers()


@router.post("/nodes/resolve", summary="Executa o consenso da cadeia válida mais longa")
async def resolve_nodes(
    blockchain: BlockchainDependency,
    nodes: NodeManagerDependency,
    realtime: RealtimeDependency,
) -> dict[str, object]:
    result = await nodes.resolve_conflicts(blockchain)
    if result["replaced"]:
        await realtime.broadcast({"type": "chain_replaced", **result})
    return result
