# WatsPoppin

App de chat self-hosted federada, cifrada ponta-a-ponta. Cada pessoa ou grupo
de amigos corre o próprio servidor; os servidores federam entre si (como
email), sem depender de infraestrutura de terceiros.

**Estado:** prova de conceito — comunicação básica de texto já funciona entre
dois ou mais utilizadores em tempo real. Ainda sem cifra, sem persistência e
sem registo a sério (ver [Limitações conhecidas](#limitações-conhecidas)).

## MVP

Mensagens de texto 1:1 cifradas entre dois utilizadores do mesmo servidor,
num só cliente (versão web). Sem federação, grupos, figurinhas ou push
nesta primeira versão — tudo o resto constrói-se por cima disto.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend (web → mobile → desktop) | React Native + Expo, TypeScript |
| Backend | Python + FastAPI (WebSockets nativos, async) |
| Base de dados | PostgreSQL, via [Peewee](https://docs.peewee-orm.com/) (síncrono, chamado a partir do FastAPI com `run_in_threadpool`) |
| Cifra ponta-a-ponta | [vodozemac](https://github.com/matrix-org/vodozemac) (Olm 1:1 + Megolm grupos) — ainda por integrar |
| Ponte nativa de cifra em mobile (pós-MVP) | Rust (JSI) — WASM não corre no motor Hermes do React Native |
| Infraestrutura | Docker, Caddy (reverse proxy + HTTPS automático via Let's Encrypt) |

## Ordem de plataformas

Web (MVP) → mobile Android → desktop Linux. iOS ainda por posicionar nesta ordem.

## Estrutura do repositório

```
WhattsPoppin/
├── frontend/    React Native + Expo (TypeScript) — npm run web|android|ios
├── backend/     FastAPI (Python) — .venv próprio, migrações em migrations/
├── Documents/   mockups de design (PDF)
├── LICENSE
├── README.md
└── projeto-chat-selfhosted.yaml   decisões de arquitetura
```

## Como correr localmente

```bash
# 1. Base de dados
cp .env.example .env    # ajusta a password
docker compose up -d postgres

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
set -a && source ../.env && set +a
pw_migrate migrate --directory migrations --database "$DATABASE_URL"
uvicorn app.main:app --reload

# 3. Frontend, noutro terminal
cd frontend
npm install
npm run web
```

Abre duas abas (ou dois dispositivos na mesma rede) para testar uma conversa
entre "Utilizador 1" e "Utilizador 2" — o registo é automático, sem ecrã de
login (ver limitações).

## O que já funciona

- Registo automático ao abrir a app (sem formulário) — cada dispositivo fica
  com um token no `localStorage`, guardado no servidor como `Device`.
- A lista de conversas mostra todos os outros utilizadores já registados
  no servidor, mesmo sem histórico nenhum entre vocês.
- Tocar num utilizador cria a conversa (se ainda não existir) e abre o chat.
- Mensagens de texto em tempo real via WebSocket, entre quantos
  utilizadores/dispositivos estiverem ligados.
- A lista actualiza-se sozinha quando alguém novo se regista, sem refresh.
- O WebSocket reconecta-se sozinho se o backend reiniciar.

## Limitações conhecidas

- **Sem cifra.** As mensagens viajam em texto simples — só para validar o
  transporte. A vodozemac ainda não está integrada.
- **Sem persistência.** As mensagens vivem só em memória no cliente (estado
  React) e passam pelo servidor sem ficarem guardadas em lado nenhum — um
  refresh da página perde o histórico da conversa.
- **Sem indicação fora da conversa.** Uma mensagem só aparece se tiveres o
  ecrã dessa conversa aberto — a lista não mostra pré-visualização real nem
  contagem de não lidas.
- **Sem registo a sério.** Não há nome escolhido, password, nem
  recuperação de conta — é "quem chega primeiro fica com o próximo número".
- **Um só dispositivo por utilizador**, sem multi-dispositivo.
- **Só localhost/rede local.** Testado só dentro de casa; ver
  `projeto-chat-selfhosted.yaml` para o desenho de produção
  (Docker, Caddy, DNS dinâmico).

## Como correr os linters e testes

**Frontend** (`cd frontend`):

```bash
npm run lint          # ESLint (eslint-config-expo)
npm run format:check  # Prettier
npm run typecheck     # tsc --noEmit
```

**Backend** (`cd backend`):

```bash
source .venv/bin/activate
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
