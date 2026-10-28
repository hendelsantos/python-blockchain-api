"""Rotas versionadas da API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from blockchain_api.api.schemas import MessageResponse, TransactionCreate
from blockchain_api.core.blockchain import (
    Blockchain,
    InsufficientFundsError,
    InvalidTransactionError,
)
from blockchain_api.core.crypto import generate_wallet

router = APIRouter(prefix="/api/v1")


def get_blockchain(request: Request) -> Blockchain:
    return request.app.state.blockchain


BlockchainDependency = Annotated[Blockchain, Depends(get_blockchain)]


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
def create_transaction(
    payload: TransactionCreate,
    blockchain: BlockchainDependency,
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

    return MessageResponse(message="Transação adicionada", data=transaction.to_dict())


@router.post("/mine/{miner}", summary="Minera as transações pendentes")
def mine_block(
    miner: str,
    blockchain: BlockchainDependency,
) -> dict[str, object]:
    try:
        block = blockchain.mine_pending_transactions(miner)
    except InvalidTransactionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return {"message": "Bloco minerado", "block": block.to_dict()}


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
