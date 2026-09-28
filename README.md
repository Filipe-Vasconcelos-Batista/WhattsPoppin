# WatsPoppin

🇬🇧 English · 🇵🇹 [Português](./README.pt.md)

A self-hosted, federated, end-to-end encrypted chat app. Each person or
group of friends runs their own server; servers federate with each other
(like email), without depending on third-party infrastructure.

**Status: v0.1.0 — MVP done.** Sign-up, login and real-time 1:1 text
messages, **end-to-end encrypted** (X3DH + Double Ratchet), with an offline
queue, message states and a live conversation list, tested across different
devices on the same network. The server only relays ciphertext. It is not
ready for real use yet: several pieces of the final design are missing (see
[Known limitations](#known-limitations), and the full status in
[`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml)).

## MVP

Encrypted 1:1 text messages between two users of the same server, in a
single client (web version). No federation, groups, stickers or push in this
first version — everything else is built on top of this.

**Done in v0.1.0.** Versions follow [SemVer](https://semver.org/): while in
`0.x`, the API and the protocol may change between versions. What is left
for `1.0.0` is in [Road to 1.0](#road-to-10).

## Next version: 0.2.0 — federation (in progress)

The goal is for `alice@server-a` and `bob@server-b` to exchange encrypted
1:1 messages across two independent servers, with offline queue, receipts
and "typing". Each client keeps talking only to its own server.

- **Our own protocol, HTTPS + JSON** (`/_federation/v1/...`). We don't use
  Matrix or XMPP, which are too large and tied to other encryption.
- **Every server-to-server request is signed** with the server's Ed25519
  key.
- **A remote server's key is pinned on first contact** (_trust on first
  use_). If it changes later, the request is refused.
- **Conversation ids never leave the server**. Events carry `user@domain`
  identifiers and each server maps them to its own conversation.
- **Messages to remote servers go through a queue** (`federation_outbox`)
  with retries and growing waits, in case the other server is down.

The phases (F0 to F7), from local authentication to "typing" across
servers, are in `next_version`, and the protocol design is in `federation`,
both in
[`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml).
Identity verification (safety number/QR) is the priority right after,
because keys start coming from servers we don't control.

## Road to 1.0

`1.0.0` is a promise: from then on the federation protocol and the data
format only change with notice and a migration path. We only call it 1.0
once a stranger can install the server at home, invite friends and talk to
another server, with no security simplification left. The focus is
**privacy**: when in doubt, the default is the most private option.

| Version | Theme |
|---|---|
| **0.2** | Federation between servers (in progress) |
| **0.3** | Contacts and invites: invite-only registration, server and contact invites (QR, link or code), contact requests, no more list of every member, safety numbers |
| **0.4** | Hardened encryption and devices: data protected on the device, "My devices" screen, app lock |
| **0.5** | Encrypted attachments (no EXIF, padded, no deduplication) and conversation with yourself |
| **0.6** | A server ready for other people: one-command installation, minimal administration, privacy settings |
| **0.7** | Apps: Android and desktop with Tauri (Linux as Flatpak, Windows) |
| **1.0-rc** | Protocol frozen, security review, installation documentation |

After 1.0: servers in **directory** mode (e.g. a company with every
colleague in the list) and **open, ephemeral** mode (e.g. a café, with the
DB wiped every day), groups, disappearing messages, linking devices by QR,
themes, iOS and macOS.

The details are in the `version_1_0` and `future_1_x` sections of
[`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml).

## Stack

| Layer | Technology |
|---|---|
| Frontend (web → Android → desktop) | React Native + Expo, TypeScript; desktop with Tauri |
| Backend | Python + FastAPI (native WebSockets, async) |
| Database | PostgreSQL, via [Peewee](https://docs.peewee-orm.com/) (synchronous, called from FastAPI with `run_in_threadpool`) |
| End-to-end encryption | Double Ratchet + X3DH implemented from scratch (Signal specs), on top of `@noble/curves`/`@noble/hashes`/`@noble/ciphers` (pure JS, no WASM) — wired into sending and receiving 1:1 messages, one session per device pair (design and decisions in the `encryption` section of [`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml)) |
| Infrastructure | Docker, Caddy (reverse proxy + automatic HTTPS via Let's Encrypt) |

## Platform order

Web (MVP) → Android → desktop with Tauri (Linux and Windows). iOS and macOS
come after 1.0.

## Repository layout

```
WhattsPoppin/
├── frontend/    React Native + Expo (TypeScript) — npm run web|android|ios
├── backend/     FastAPI (Python) — its own .venv, migrations in migrations/
├── Documents/   design mockups (PDF) + project-chat-selfhosted.yaml (EN) / projeto-chat-selfhosted.yaml (PT)
├── LICENSE
├── README.md    (English)
└── README.pt.md (Portuguese)
```

## Running locally

```bash
# 1. Database
cp .env.example .env
docker compose up -d postgres

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
set -a && source ../.env && set +a
pw_migrate migrate --directory migrations --database "$DATABASE_URL"
uvicorn app.main:app --reload

# 3. Frontend (in another terminal)
cd frontend
nvm use
npm install
npm run web
```

Open the app, create an account under "Criar conta" (username + password,
at least 12 characters) and repeat in another tab/device with another
username — the two show up in each other's conversation list.

## What already works

- Real sign-up and login (username + password), with the session resumed
  automatically from a token stored on the device.
- Every request and the WebSocket require that token. The server works out
  who you are from it and only stores its hash, and only the participants
  of a conversation can send to it or see its devices.
- The conversation list shows every other user already registered on the
  server, even with no history between you.
- Tapping a user creates the conversation (if it doesn't exist yet) and
  opens the chat.
- Real-time text messages over WebSocket, between however many
  users/devices are connected.
- **End-to-end encryption:** each device publishes its keys on sign-up/login;
  the first message opens an X3DH session and from then on every message
  uses a new key (Double Ratchet). The sender encrypts one envelope per
  recipient device; the server delivers to each only its own and never sees
  the text.
- The list updates by itself when someone new signs up, no refresh.
- **Live conversation list:** each conversation shows the last message, the
  time ("14:32", "Yesterday", "Tue") and how many are unread; the one that
  received or sent the most recent message moves to the top. On the web,
  the browser tab shows the unread total, e.g. "(3) WhattsPoppin".
- **"Typing"**: while the other person types, three dots show at the bottom
  of the conversation and "typing…" in the list. It is an ephemeral event
  the server never stores.
- **Editable display name** in "My profile" (the settings button in the
  list). Others see the new name right away, no refresh; the username you
  log in with doesn't change.
- The WebSocket reconnects by itself if the backend restarts.
- **Offline queue:** messages for someone who isn't connected are kept on
  the server (only the encrypted envelope) and delivered when the device
  connects. Each device confirms (acks) what it received and only then does
  the message leave the server; anything never confirmed expires after 30
  days.
- **Message states** on the bubble, like WhatsApp: clock (hasn't left the
  device yet), ✓ (the server stored it), ✓✓ (reached one of the
  recipient's devices), coloured ✓✓ (read). If your socket is down, the
  message waits in a local outbox and goes out by itself when it
  reconnects — encrypted only once, resent with the same bytes.
- Messages persist on the device (per user) and survive a page refresh.

## Known limitations

- **No identity verification** (safety number / QR). Encryption protects
  against network eavesdroppers, but not against a compromised server that
  swaps someone's keys.
- **Encryption only in 1:1, with known rough edges** (details in
  `encryption.known_limitations` in
  [`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml)):
  if both sides open a session at the same time, the messages that cross
  may not decrypt; there is no signed prekey rotation or automatic one-time
  prekey replenishment; and each login creates a new device, which senders
  also start encrypting for.
- **No key backup.** Private keys and sessions live only in the
  browser's/device's local storage — clearing that storage means losing
  that device's identity.
- **Local storage without its own protection yet.** Keeping decrypted
  messages on the device is normal (WhatsApp and Signal do the same:
  end-to-end encryption protects the path between devices, not the device
  itself). The difference is that they protect that storage (Signal
  encrypts its local database with a key kept in the operating system's
  vault). Here, on the web, the messages **and the private keys** are in
  `localStorage` unencrypted — readable by any script on the page and by
  anyone with access to the browser profile, and they stay there after
  closing the app. Don't use it on a shared machine for now. The design to
  fix this (outside the MVP) is in `encryption.on_device_data_protection`
  in
  [`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml).
- **Read receipts always on.** There is no option to turn them off yet
  (like in WhatsApp), and no visible "failed" state — a message that can't
  be encrypted (e.g. the recipient has no keys) keeps the clock.
- **No nicknames or name ambiguity detection.**
- **A single device per user**, no real multi-device.
- **No federation** (in progress, see above): conversations only within the
  same server.
- **Open registration**, with no invite code or admin approval, and the
  conversation list shows every member of the server. Changes in 0.3.
- **Conversation with yourself doesn't work** yet. Fixed in 0.5.
- **Localhost/local network only.** Tested only at home; see
  `Documents/project-chat-selfhosted.yaml` for the production design
  (Docker, Caddy, dynamic DNS).

## Running linters and tests

**Frontend** (`cd frontend`):

```bash
npm run lint          # ESLint (eslint-config-expo)
npm run format:check  # Prettier
npm run typecheck     # tsc --noEmit
npm run test          # Vitest (encryption: primitives, X3DH, Double Ratchet, sessions)
```

**Backend** (`cd backend`):

```bash
source .venv/bin/activate
ruff check .
mypy app
pytest -q
```

`pytest` never runs against the dev DB: `tests/conftest.py` requires
`TEST_DATABASE_URL` in `.env` (see `.env.example`) and refuses to run if the
DB name doesn't end in `_test`. Create that DB once:

```bash
docker exec -it whattspoppin-postgres createdb -U whattspoppin whattspoppin_test
```

## License

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)

## Documentation

Every architecture decision, the reasoning behind each one, the current
implementation status and what is still missing are in
[`Documents/project-chat-selfhosted.yaml`](./Documents/project-chat-selfhosted.yaml)
(in Portuguese: [`Documents/projeto-chat-selfhosted.yaml`](./Documents/projeto-chat-selfhosted.yaml)).
The documentation is bilingual and both versions always change together.
