# Python Blockchain API

Uma blockchain educacional com **Python**, **FastAPI** e **proof-of-work**, criada como
projeto de portfólio backend. O projeto demonstra modelagem de domínio, API REST,
concorrência básica, persistência SQL, testes automatizados, containerização e integração contínua.

> Este projeto é educacional. As carteiras usam Ed25519 e os nós usam a regra da
> cadeia válida mais longa, mas isso não constitui consenso seguro para uso financeiro real.

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
- carteiras Ed25519 geradas no navegador e transações assinadas;
- validação de assinatura, endereço e nonce contra ataques de replay;
- registro de peers e consenso pela cadeia válida mais longa;
- atualizações de blocos em tempo real por WebSocket;
- segundo nó isolado e opcional no Docker Compose;
- migrações de banco com Alembic;
- testes unitários e de integração;
- Docker e pipeline de CI no GitHub Actions.

## Tecnologias

- Python 3.11+
- FastAPI e Uvicorn
- Pydantic
- SQLAlchemy, Alembic e Psycopg
- Cryptography e Web Crypto API
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

### Executar uma rede com dois nós

```bash
docker compose --profile network up --build
```

O primeiro nó fica em `http://localhost:8000` e o segundo em
`http://localhost:8002`, cada um com seu próprio PostgreSQL. Registre o segundo nó no
primeiro usando `http://node2:8000`, que é o endereço interno do Docker:

```bash
curl -X POST http://localhost:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"urls":["http://node2:8000"]}'

curl -X POST http://localhost:8000/api/v1/nodes/resolve
```

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

## Teste rápido pelo dashboard

1. Abra http://localhost:8000.
2. Em **Carteira criptográfica**, clique em **Gerar nova carteira**.
3. Use o endereço preenchido automaticamente para minerar um bloco.
4. Crie uma transação; o navegador a assinará com Ed25519 antes de enviá-la.
5. Minere novamente e confira os saldos e a assinatura no explorador.

A chave privada fica apenas no `sessionStorage` da aba. Fechar a aba remove o acesso à
carteira; esse comportamento é intencional nesta versão educacional.

Para minerar diretamente pela API:

```bash
curl -X POST http://localhost:8000/api/v1/mine/SEU_ENDERECO
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
| `POST` | `/api/v1/wallets/generate` | Gera chaves Ed25519 para uso via API |
| `GET` | `/api/v1/wallets/{address}/balance` | Consulta o saldo de uma carteira |
| `GET` | `/api/v1/nodes` | Identidade e peers do nó |
| `POST` | `/api/v1/nodes/register` | Registra novos peers |
| `POST` | `/api/v1/nodes/resolve` | Executa o consenso entre peers |
| `WS` | `/ws/blocks` | Eventos de blocos e transações em tempo real |

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

- importar, exportar e recuperar carteiras com segurança;
- descoberta automática e autenticação entre peers;
- consenso tolerante a falhas bizantinas;
- autenticação, observabilidade e deploy em nuvem.

## Licença

Distribuído sob a licença MIT.
