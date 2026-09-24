# WatsPoppin

App de chat self-hosted federada, cifrada ponta-a-ponta. Cada pessoa ou grupo
de amigos corre o próprio servidor; os servidores federam entre si (como
email), sem depender de infraestrutura de terceiros.

**Estado:** pré-alpha — estrutura inicial dos projetos, ainda sem funcionalidades.

## MVP

Mensagens de texto 1:1 cifradas entre dois utilizadores do mesmo servidor,
num só cliente (versão web). Sem federação, grupos, figurinhas ou push
nesta primeira versão — tudo o resto constrói-se por cima disto.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend (web → mobile → desktop) | React Native + Expo, TypeScript |
| Backend | Python + FastAPI (WebSockets nativos, async) |
| Base de dados | PostgreSQL |
| Cifra ponta-a-ponta | [vodozemac](https://github.com/matrix-org/vodozemac) (Olm 1:1 + Megolm grupos) |
| Ponte nativa de cifra em mobile (pós-MVP) | Rust (JSI) — WASM não corre no motor Hermes do React Native |
| Infraestrutura | Docker, Caddy (reverse proxy + HTTPS automático via Let's Encrypt) |

## Ordem de plataformas

Web (MVP) → mobile Android → desktop Linux. iOS ainda por posicionar nesta ordem.

## Estrutura do repositório

```
WattsPopin/
├── frontend/    React Native + Expo (TypeScript) — npm run web|android|ios
├── backend/     FastAPI (Python) — .venv próprio
├── LICENSE
├── README.md
└── projeto-chat-selfhosted.yaml   decisões de arquitetura
```

## Como correr os linters e testes

**Frontend** (`cd frontend`):

```bash
npm run lint          # ESLint (eslint-config-expo)
npm run format:check  # Prettier
npm run typecheck     # tsc --noEmit
```

**Backend** (`cd backend`):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

ruff check .      # lint
mypy app          # verificação de tipos
pytest -q         # testes
```

## Licença

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)

## Documentação

Todas as decisões de arquitetura, o porquê de cada uma e o que ainda falta
decidir estão em
[`projeto-chat-selfhosted.yaml`](./projeto-chat-selfhosted.yaml).
