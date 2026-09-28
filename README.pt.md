# WatsPoppin

🇬🇧 [English](./README.md) · 🇵🇹 Português

App de chat self-hosted federada, cifrada ponta-a-ponta. Cada pessoa ou grupo
de amigos corre o próprio servidor; os servidores federam entre si (como
email), sem depender de infraestrutura de terceiros.

**Estado: v0.1.0 — MVP concluído.** Registo, login e mensagens de texto 1:1
em tempo real, **cifradas ponta-a-ponta** (X3DH + Double Ratchet), com fila
offline, estados de mensagem e lista de conversas viva, testado entre
dispositivos diferentes na mesma rede. O servidor só encaminha ciphertext.
Ainda não é para uso real: faltam várias peças do desenho final (ver
[Limitações conhecidas](#limitações-conhecidas), e o estado completo em
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)).

## MVP

Mensagens de texto 1:1 cifradas entre dois utilizadores do mesmo servidor,
num só cliente (versão web). Sem federação, grupos, figurinhas ou push
nesta primeira versão — tudo o resto constrói-se por cima disto.

**Cumprido na v0.1.0.** As versões seguem o [SemVer](https://semver.org/lang/pt-BR/):
enquanto estiver em `0.x`, a API e o protocolo podem mudar entre versões.
O que falta para a `1.0.0` está em [Caminho até à 1.0](#caminho-até-à-10).

## Próxima versão: 0.2.0 — federação (em curso)

O objetivo é que `alice@servidor-a` e `bob@servidor-b` troquem mensagens 1:1
cifradas entre dois servidores independentes, com fila offline, recibos e
"a escrever". Cada cliente continua a falar só com o próprio servidor.

- **Protocolo próprio, HTTPS + JSON** (`/_federation/v1/...`). Não usamos
  Matrix nem XMPP, que são demasiado grandes e presos a outra cifra.
- **Cada pedido entre servidores vai assinado** com a chave Ed25519 do
  servidor.
- **A chave de um servidor remoto fica fixada no primeiro contacto**
  (_trust on first use_). Se mudar mais tarde, o pedido é recusado.
- **Os ids de conversa não saem do servidor**. Os eventos levam
  identificadores `user@domínio` e cada servidor traduz para a sua conversa.
- **Mensagens para servidores remotos passam por uma fila**
  (`federation_outbox`) com novas tentativas e espera crescente, se o outro
  servidor estiver em baixo.

As fases (F0 a F7), da autenticação local até ao "a escrever" entre
servidores, estão em `proxima_versao` e o desenho do protocolo está em
`federacao`, ambos no
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml).
A verificação de identidade (número de segurança/QR) é a prioridade logo a
seguir, porque as chaves passam a vir de servidores que não controlamos.

## Caminho até à 1.0

A `1.0.0` é uma promessa: daí em diante o protocolo de federação e o
formato dos dados só mudam com aviso e caminho de migração. Só lhe
chamamos 1.0 quando um desconhecido conseguir instalar o servidor em
casa, convidar amigos e falar com outro servidor, sem sobrar nenhuma
simplificação de segurança. O foco é a **privacidade**: na dúvida, a
opção por omissão é a mais privada.

| Versão | Tema |
|---|---|
| **0.2** | Federação entre servidores (em curso) |
| **0.3** | Contactos e convites: registo só por convite, convites de servidor e de contacto (QR, link ou código), pedidos de contacto, fim da lista com todos os membros, números de segurança |
| **0.4** | Cifra endurecida e dispositivos: dados protegidos no dispositivo, ecrã "Os meus dispositivos", bloqueio da app |
| **0.5** | Anexos cifrados (sem EXIF, com padding, sem deduplicação) e conversa consigo próprio |
| **0.6** | Servidor pronto para outras pessoas: instalação com um comando, administração mínima, definições de privacidade |
| **0.7** | Apps: Android e desktop com Tauri (Linux em Flatpak, Windows) |
| **1.0-rc** | Protocolo congelado, revisão de segurança, documentação de instalação |

Para depois da 1.0: servidores em modo **diretório** (ex. uma empresa com
todos os colegas na lista) e **aberto e efémero** (ex. um café, com a BD
apagada todos os dias), grupos, mensagens temporárias, ligar dispositivos
por QR, temas, iOS e macOS.

O detalhe está nas secções `versao_1_0` e `futuro_1_x` do
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml).

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend (web → Android → desktop) | React Native + Expo, TypeScript; desktop com Tauri |
| Backend | Python + FastAPI (WebSockets nativos, async) |
| Base de dados | PostgreSQL, via [Peewee](https://docs.peewee-orm.com/) (síncrono, chamado a partir do FastAPI com `run_in_threadpool`) |
| Cifra ponta-a-ponta | Double Ratchet + X3DH implementados de raiz (specs do Signal), sobre `@noble/curves`/`@noble/hashes`/`@noble/ciphers` (JS puro, sem WASM) — ligado ao envio e receção de mensagens 1:1, uma sessão por par de dispositivos (desenho e decisões na secção `cifra` de [`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)) |
| Infraestrutura | Docker, Caddy (reverse proxy + HTTPS automático via Let's Encrypt) |

## Ordem de plataformas

Web (MVP) → Android → desktop com Tauri (Linux e Windows). iOS e macOS
ficam para depois da 1.0.

## Estrutura do repositório

```
WhattsPoppin/
├── frontend/    React Native + Expo (TypeScript) — npm run web|android|ios
├── backend/     FastAPI (Python) — .venv próprio, migrações em migrations/
├── dev/         scripts de desenvolvimento (federation.sh)
├── Documents/   mockups de design (PDF) + projeto-chat-selfhosted.yaml (PT) / project-chat-selfhosted.yaml (EN)
├── LICENSE
├── README.md    (inglês)
└── README.pt.md (português)
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
uvicorn app.main:app --reload --host 0.0.0.0

# 3. Frontend (noutro terminal)
cd frontend
nvm use
npm install
npm run web
```

Abre a app, cria uma conta em "Criar conta" (username de 3 a 32 caracteres
com `a-z 0-9 . _ -`, password com pelo menos 12) e repete noutra
aba/dispositivo com outro username — os dois aparecem um ao outro na lista
de conversas.

O frontend descobre sozinho onde está o backend: na web usa o mesmo host
da página (abrir `http://<IP-da-máquina>:8081` noutro dispositivo da rede
também funciona), por isso não há IPs escritos no código. O `--host 0.0.0.0`
do uvicorn é o que deixa os outros dispositivos da rede ligarem-se.

### Dois servidores em dev (para a federação)

Um só comando, na raiz do projeto:

```bash
dev/federation.sh
```

Arranca o Postgres, cria a BD do servidor B se ainda não existir, e põe a
correr os quatro processos no mesmo terminal, cada linha com o seu prefixo:

| Prefixo | O quê | Endereço |
|---|---|---|
| `[A]` | servidor A (BD de dev) | `localhost:8001` |
| `[B]` | servidor B (BD `whattspoppin_b`) | `localhost:8002` |
| `[web-a]` | cliente web do A | http://localhost:8091 |
| `[web-b]` | cliente web do B | http://localhost:8092 |

**Ctrl+C** pára tudo; se um dos processos morrer (ex. uma porta ocupada), os
outros também param. Cada cliente tem o seu próprio `localStorage`, por
isso as sessões não se misturam.

Para correr só uma peça: `backend/dev/run-server.sh a|b` (servidor, com
migrações) ou `npm run web:a|web:b` dentro de `frontend/`. Os dois
servidores ainda não falam um com o outro — isso vem nas fases seguintes da
0.2.0.

## O que já funciona

- Registo e login reais (username + password), com sessão retomada
  automaticamente a partir de um token guardado no dispositivo.
- Cada conta tem um identificador `user@domínio` (ex. `alice@casa.pt`),
  visível em "O meu perfil" — é o que vais partilhar com contactos de
  outros servidores.
- Todos os pedidos e o WebSocket exigem esse token. O servidor tira dele
  quem és e só guarda o hash, e só quem está numa conversa consegue enviar
  para ela ou ver os dispositivos dela.
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
- **Nome de exibição editável** em "O meu perfil" (o botão de definições na
  lista). Os outros veem o nome novo logo, sem refresh; o nome de
  utilizador com que entras não muda.
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
- **Sem federação** (em curso, ver acima): só conversas dentro do mesmo
  servidor.
- **Registo aberto**, sem código de convite nem aprovação de admin, e a
  lista de conversas mostra todos os membros do servidor. Muda na 0.3.
- **Conversa consigo próprio não funciona** ainda. Resolve-se na 0.5.
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
[`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)
(em inglês: [`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml)).
A documentação é bilingue e as duas versões mudam sempre juntas.
