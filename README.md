# WhattsPoppin

App de chat self-hosted federada, cifrada ponta-a-ponta. Cada pessoa ou grupo
de amigos corre o próprio servidor; os servidores federam entre si (como
email), sem depender de infraestrutura de terceiros.

**Estado:** pré-alpha — fase de design, ainda sem código.

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

Web (MVP) → mobile Android → desktop Linux.

## Licença

[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) 
## Documentação

Todas as decisões de arquitetura, o porquê de cada uma e o que ainda falta
decidir estão em
[`projeto-chat-selfhosted.yaml`](./projeto-chat-selfhosted.yaml).
