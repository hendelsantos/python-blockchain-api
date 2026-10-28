"""Rotas versionadas da API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from blockchain_api.api.schemas import MessageResponse, TransactionCreate
from blockchain_api.core.blockchain import Blockchain, InvalidTransactionError

router = APIRouter(prefix="/api/v1")


def get_blockchain(request: Request) -> Blockchain:
    return request.app.state.blockchain


BlockchainDependency = Annotated[Blockchain, Depends(get_blockchain)]


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
        )
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
