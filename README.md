# WatsPoppin

App de chat self-hosted federada, cifrada ponta-a-ponta. Cada pessoa ou grupo
de amigos corre o próprio servidor; os servidores federam entre si (como
email), sem depender de infraestrutura de terceiros.

**Estado:** prova de conceito — registo, login e mensagens de texto 1:1 em
tempo real, **cifradas ponta-a-ponta** (X3DH + Double Ratchet), testado
entre dispositivos diferentes na mesma rede. O servidor só encaminha
ciphertext. Ainda faltam várias peças do desenho final (ver
[Limitações conhecidas](#limitações-conhecidas), e o estado completo em
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
| Cifra ponta-a-ponta | Double Ratchet + X3DH implementados de raiz (specs do Signal), sobre `@noble/curves`/`@noble/hashes`/`@noble/ciphers` (JS puro, sem WASM) — ligado ao envio e receção de mensagens 1:1, uma sessão por par de dispositivos (desenho e decisões na secção `cifra` de [`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)) |
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
cp .env.example .env
docker compose up -d postgres

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
set -a && source ../.env && set +a
pw_migrate migrate --directory migrations --database "$DATABASE_URL"
uvicorn app.main:app --reload


cd frontend
nvm use
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
- **Cifra ponta-a-ponta:** cada dispositivo publica as suas chaves ao
  criar conta/fazer login; a primeira mensagem abre uma sessão X3DH e
  daí em diante cada mensagem usa uma chave nova (Double Ratchet). Quem
  envia cifra um envelope por cada dispositivo do destinatário; o
  servidor entrega a cada um só o seu e nunca vê o texto.
- A lista atualiza-se sozinha quando alguém novo se regista, sem refresh.
- **Lista de conversas viva:** cada conversa mostra a última mensagem, a
  hora ("14:32", "Ontem", "Ter") e quantas estão por ler; a que recebeu ou
  enviou a mensagem mais recente sobe para o topo. Na web, o separador do
  browser mostra o total por ler, por exemplo "(3) WhattsPoppin".
- **"A escrever"**: enquanto o outro escreve, aparecem três pontos no fundo
  da conversa e "a escrever…" na lista. É um evento efémero, que o servidor
  nunca guarda.
- O WebSocket reconecta-se sozinho se o backend reiniciar.
- **Fila offline:** mensagens para quem não está ligado ficam guardadas no
  servidor (só o envelope cifrado) e são entregues quando o dispositivo se
  liga. Cada dispositivo confirma (ack) o que recebeu e só então a mensagem
  sai do servidor; o que nunca é confirmado expira ao fim de 30 dias.
- **Estados de mensagem** na bolha, como no WhatsApp: relógio (ainda não
  saiu do dispositivo), ✓ (o servidor guardou), ✓✓ (chegou a um
  dispositivo do destinatário), ✓✓ colorido (lida). Se o teu socket estiver
  em baixo, a mensagem fica numa outbox local e sai sozinha quando voltar a
  ligar — cifrada uma só vez, reenviada com os mesmos bytes.
- Mensagens persistem no dispositivo (por utilizador), sobrevivem a um
  refresh da página.

## Limitações conhecidas

- **Sem verificação de identidade** (número de segurança / QR). A cifra
  protege contra quem escuta a rede, mas não contra um servidor
  comprometido que troque as chaves de alguém.
- **Cifra só em 1:1, e com arestas conhecidas** (detalhe em
  `cifra.limitacoes_conhecidas` no
  [`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)):
  se os dois lados abrirem sessão ao mesmo tempo, as mensagens que se
  cruzarem podem não decifrar; não há rotação da signed prekey nem
  reposição automática das one-time prekeys; e cada login cria um
  dispositivo novo, para o qual quem envia também passa a cifrar.
- **Sem backup de chaves.** As chaves privadas e as sessões vivem só no
  armazenamento local do browser/dispositivo — limpar esse armazenamento
  é perder a identidade desse dispositivo.
- **Armazenamento local ainda sem proteção própria.** Guardar as mensagens
  decifradas no dispositivo é o normal (o WhatsApp e o Signal fazem o
  mesmo: a cifra ponta-a-ponta protege o caminho entre dispositivos, não o
  dispositivo em si). A diferença é que eles protegem esse armazenamento
  (o Signal cifra a base de dados local com uma chave guardada no cofre do
  sistema operativo). Aqui, na web, as mensagens **e as chaves privadas**
  estão no `localStorage` sem cifra — legíveis por qualquer script na
  página e por quem aceder ao perfil do browser, e ficam lá depois de
  fechar a app. Não usar numa máquina partilhada por enquanto. O desenho
  para resolver isto (fora do MVP) está em
  `cifra.protecao_dos_dados_no_dispositivo` no
  [`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml).
- **Recibos de leitura sempre ligados.** Ainda não há a opção de os
  desligar (como no WhatsApp), nem estado "falhou" visível — uma mensagem
  que não se consegue cifrar (ex.: destinatário sem chaves) fica com o
  relógio.
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
npm run test          # Vitest (cifra: primitivos, X3DH, Double Ratchet, sessões)
```

**Backend** (`cd backend`):

```bash
source .venv/bin/activate
ruff check .
mypy app
pytest -q
```

O `pytest` nunca corre contra a BD de dev: `tests/conftest.py` exige
`TEST_DATABASE_URL` no `.env` (ver `.env.example`) e recusa-se a correr se
o nome da BD não acabar em `_test`. Criar essa BD uma vez:

```bash
docker exec -it whattspoppin-postgres createdb -U whattspoppin whattspoppin_test
```

## Licença

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)

## Documentação

Todas as decisões de arquitetura, o porquê de cada uma, o estado actual da
implementação e o que ainda falta estão em
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml).
