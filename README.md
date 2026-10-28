# Python Blockchain API

Uma blockchain educacional com **Python**, **FastAPI** e **proof-of-work**, criada como
projeto de portfólio backend. O projeto demonstra modelagem de domínio, API REST,
concorrência básica, persistência SQL, testes automatizados, containerização e integração contínua.

> Este projeto é educacional. As carteiras são identificadores textuais e ainda não
> possuem chaves criptográficas ou garantias necessárias para uso financeiro real.

## O que já funciona

- criação de transações com validação de domínio;
- fila de transações pendentes;
- mineração de blocos com proof-of-work configurável;
- recompensa para o minerador;
- encadeamento por SHA-256 e validação de integridade;
- API documentada automaticamente com OpenAPI/Swagger;
- dashboard web responsivo para visualizar e operar a blockchain;
- persistência com PostgreSQL em produção e SQLite no desenvolvimento local;
- carteiras, consulta de saldo e bloqueio de gasto duplo pendente;
- migrações de banco com Alembic;
- testes unitários e de integração;
- Docker e pipeline de CI no GitHub Actions.

## Tecnologias

- Python 3.11+
- FastAPI e Uvicorn
- Pydantic
- SQLAlchemy, Alembic e Psycopg
- PostgreSQL e SQLite
- Pytest e coverage
- Ruff
- Docker
- GitHub Actions

## Como executar com Docker Compose

Este é o caminho recomendado. Ele inicia a API e o PostgreSQL, aplica as migrações
e preserva os dados em um volume Docker.

```bash
docker compose up --build
```

Acesse:

- Dashboard: http://localhost:8000
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Para usar outra porta, execute `API_PORT=8123 docker compose up --build`.

## Como executar localmente com SQLite

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn blockchain_api.main:app --reload
```

Acesse:

- Dashboard: http://localhost:8000
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Teste rápido

Primeiro minere para que `alice` receba a recompensa da rede:

```bash
curl -X POST http://localhost:8000/api/v1/mine/alice
```

Depois transfira parte do saldo:

```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"sender":"alice","recipient":"bob","amount":"0.50"}'
```

Minere o próximo bloco:

```bash
curl -X POST http://localhost:8000/api/v1/mine/miner-01
```

Consulte e valide a cadeia:

```bash
curl http://localhost:8000/api/v1/chain
curl http://localhost:8000/api/v1/chain/validate
curl http://localhost:8000/api/v1/wallets
curl http://localhost:8000/api/v1/wallets/alice/balance
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
| `GET` | `/api/v1/wallets` | Lista carteiras e saldos |
| `GET` | `/api/v1/wallets/{address}/balance` | Consulta o saldo de uma carteira |

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
├── infrastructure/ # SQLAlchemy e repositório persistente
├── static/    # dashboard HTML, CSS e JavaScript
└── main.py    # composição da aplicação
```

## Próximas evoluções

- assinar transações com criptografia assimétrica;
- propagar blocos entre nós via WebSocket;
- implementar consenso entre nós;
- autenticação, observabilidade e deploy em nuvem.

## Licença

Distribuído sob a licença MIT.
