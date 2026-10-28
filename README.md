# Python Blockchain API

Uma blockchain educacional com **Python**, **FastAPI** e **proof-of-work**, criada como
projeto de portfólio backend. O projeto demonstra modelagem de domínio, API REST,
concorrência básica, testes automatizados, containerização e integração contínua.

> Este projeto é educacional. Ele não implementa consenso distribuído, carteiras
> criptográficas ou garantias necessárias para uso financeiro real.

## O que já funciona

- criação de transações com validação de domínio;
- fila de transações pendentes;
- mineração de blocos com proof-of-work configurável;
- recompensa para o minerador;
- encadeamento por SHA-256 e validação de integridade;
- API documentada automaticamente com OpenAPI/Swagger;
- dashboard web responsivo para visualizar e operar a blockchain;
- testes unitários e de integração;
- Docker e pipeline de CI no GitHub Actions.

## Tecnologias

- Python 3.11+
- FastAPI e Uvicorn
- Pydantic
- Pytest e coverage
- Ruff
- Docker
- GitHub Actions

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn blockchain_api.main:app --reload
```

Acesse:

- Dashboard: http://localhost:8000
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Teste rápido

Crie uma transação:

```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"sender":"alice","recipient":"bob","amount":"10.50"}'
```

Minere o próximo bloco:

```bash
curl -X POST http://localhost:8000/api/v1/mine/miner-01
```

Consulte e valide a cadeia:

```bash
curl http://localhost:8000/api/v1/chain
curl http://localhost:8000/api/v1/chain/validate
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Estado da aplicação |
| `GET` | `/api/v1/chain` | Lista a blockchain |
| `GET` | `/api/v1/chain/validate` | Valida hashes e proof-of-work |
| `GET` | `/api/v1/transactions/pending` | Lista transações pendentes |
| `POST` | `/api/v1/transactions` | Cria uma transação |
| `POST` | `/api/v1/mine/{miner}` | Minera um bloco |

## Qualidade

```bash
pytest
ruff check .
ruff format --check .
```

## Arquitetura

```text
src/blockchain_api/
├── api/       # rotas HTTP e schemas
├── core/      # serviço da blockchain
├── domain/    # Block e Transaction
└── main.py    # composição da aplicação
```

## Próximas evoluções

- persistir a cadeia em PostgreSQL;
- assinar transações com criptografia assimétrica;
- adicionar carteiras, saldos e prevenção de gasto duplo;
- propagar blocos entre nós via WebSocket;
- implementar consenso entre nós;
- autenticação, observabilidade e deploy em nuvem.

## Licença

Distribuído sob a licença MIT.
