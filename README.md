# WatsPoppin

App de chat self-hosted federada, cifrada ponta-a-ponta. Cada pessoa ou grupo
de amigos corre o próprio servidor; os servidores federam entre si (como
email), sem depender de infraestrutura de terceiros.

**Estado:** prova de conceito — registo, login e mensagens de texto em tempo
real já funcionam entre vários utilizadores, testado entre dispositivos
diferentes na mesma rede. Ainda sem cifra e sem várias peças do desenho
final (ver [Limitações conhecidas](#limitações-conhecidas), e o estado
completo em
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)).

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
| Cifra ponta-a-ponta | Double Ratchet + X3DH implementados de raiz (specs do Signal), sobre `@noble/curves`/`@noble/hashes`/`@noble/ciphers` (JS puro, sem WASM) — primitivos e publicação de chaves prontos, falta ligar ao envio/receção de mensagens (ver [`Documents/plano-cifra-ponta-a-ponta.md`](./Documents/plano-cifra-ponta-a-ponta.md)) |
| Infraestrutura | Docker, Caddy (reverse proxy + HTTPS automático via Let's Encrypt) |

## Ordem de plataformas

Web (MVP) → mobile Android → desktop Linux. iOS ainda por posicionar nesta ordem.

## Estrutura do repositório

```
WhattsPoppin/
├── frontend/    React Native + Expo (TypeScript) — npm run web|android|ios
├── backend/     FastAPI (Python) — .venv próprio, migrações em migrations/
├── Documents/   mockups de design (PDF) + projeto-chat-selfhosted.yaml
├── LICENSE
└── README.md
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
nvm use          # fixa o Node deste projecto (24, ver .nvmrc)
npm install
npm run web
```

Abre a app, cria uma conta em "Criar conta" (username + password, mínimo 12
caracteres) e repete noutra aba/dispositivo com outro username — os dois
aparecem um ao outro na lista de conversas.

## O que já funciona

- Registo e login reais (username + password), com sessão retomada
  automaticamente a partir de um token guardado no dispositivo.
- A lista de conversas mostra todos os outros utilizadores já registados
  no servidor, mesmo sem histórico nenhum entre vocês.
- Tocar num utilizador cria a conversa (se ainda não existir) e abre o chat.
- Mensagens de texto em tempo real via WebSocket, entre quantos
  utilizadores/dispositivos estiverem ligados.
- A lista atualiza-se sozinha quando alguém novo se regista, sem refresh.
- O WebSocket reconecta-se sozinho se o backend reiniciar.
- Mensagens persistem no dispositivo (por utilizador), sobrevivem a um
  refresh da página.

## Limitações conhecidas

- **Sem cifra ligada ao envio/receção de mensagens.** As mensagens ainda
  viajam em texto simples — a implementação própria de Double Ratchet +
  X3DH está em curso (ver
  [`Documents/plano-cifra-ponta-a-ponta.md`](./Documents/plano-cifra-ponta-a-ponta.md)):
  primitivos criptográficos e publicação das chaves de cada dispositivo já
  feitos, falta X3DH, Double Ratchet e ligar tudo a `sendMessage`/receção.
- **Sem indicação fora da conversa.** Uma mensagem só aparece se tiveres o
  ecrã dessa conversa aberto — a lista não mostra pré-visualização real nem
  contagem de não lidas.
- **Sem estados de mensagem.** Não há pending/delivered/read, nem fila de
  entrega quando o destinatário está offline — a mensagem perde-se.
- **Sem alcunhas nem deteção de ambiguidade de nomes.**
- **Um só dispositivo por utilizador**, sem multi-dispositivo a sério.
- **Registo aberto**, sem código de convite nem aprovação de admin.
- **Só localhost/rede local.** Testado só dentro de casa; ver
  `Documents/projeto-chat-selfhosted.yaml` para o desenho de produção
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

Todas as decisões de arquitetura, o porquê de cada uma, o estado actual da
implementação e o que ainda falta estão em
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml).
