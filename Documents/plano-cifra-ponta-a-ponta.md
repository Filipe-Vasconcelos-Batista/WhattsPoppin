# Plano: cifra ponta-a-ponta (Double Ratchet + X3DH)

> Retomar uma sessão futura: lê este ficheiro inteiro antes de tocar em
> código. A secção **"Onde ficámos"**, no fim, diz exactamente o próximo
> passo.

## Porquê este caminho (contexto, para não repetir a investigação)

- Escolhemos originalmente a **vodozemac** (Olm/Megolm) em vez da libsignal,
  por ter API "estável, documentada, para uso por terceiros".
- Ao investigar a sério (Set 2026), descobrimos que os *bindings* de
  JavaScript da vodozemac estão todos parados: o oficial
  (`matrix-org/vodozemac-bindings`) está explicitamente **abandonado**, e os
  forks da comunidade (`@towns-protocol/vodozemac`, `vodozemac-wasm-bindings`)
  têm uma única versão publicada, há mais de um ano, sem actualizações. A
  única opção JS activamente mantida (`@matrix-org/matrix-sdk-crypto-wasm`) é
  o `OlmMachine` inteiro do Matrix, preso a conceitos do protocolo deles
  (salas, `UserId`/`DeviceId` no formato Matrix) - pesado demais e mal
  encaixado no nosso backend próprio.
- Decisão: **implementar nós próprios o Double Ratchet + X3DH**, seguindo à
  risca as especificações publicadas pelo Signal, em cima de primitivos
  criptográficos já auditados (nunca inventar cifra nossa, só a lógica de
  encadeamento de chaves).
- Vantagem extra descoberta: as bibliotecas escolhidas são **JavaScript puro,
  sem WASM** - o que resolve também o problema já identificado da cifra não
  correr no motor Hermes do React Native em mobile. Um problema a menos.

## Especificações de referência (ler antes de programar cada peça)

- Double Ratchet: https://signal.org/docs/specifications/doubleratchet/
- X3DH: https://signal.org/docs/specifications/x3dh/

## Primitivos escolhidos

| Peça | Biblioteca | Uso |
|---|---|---|
| X25519 (Diffie-Hellman) | `@noble/curves` | `DH()` em todo o lado |
| HKDF-SHA256 | `@noble/hashes` | `KDF_RK`, `KDF` do X3DH |
| HMAC-SHA256 | `@noble/hashes` | `KDF_CK` |
| AEAD da mensagem | `@noble/ciphers` (ChaCha20-Poly1305) | cifrar/decifrar o texto em si |

Instalar no frontend:
```bash
cd frontend
npx expo install @noble/curves @noble/hashes @noble/ciphers
```

## Mudanças ao modelo de dados (backend)

**`Device`** (`backend/app/models/device.py`) - novos campos:
- `identity_key: BlobField` - chave pública de identidade (IK), permanente
- `signed_prekey: BlobField` - prekey assinada (SPK), pública
- `signed_prekey_signature: BlobField` - assinatura da SPK pela IK
- `signed_prekey_id: IntegerField` - para poder trocar a SPK sem ambiguidade

**Nova tabela `OneTimePrekey`** (`backend/app/models/one_time_prekey.py`):
- `id: UUIDField`
- `device: ForeignKeyField(Device)`
- `key_id: IntegerField`
- `public_key: BlobField`
- apagada da BD assim que é entregue a alguém (uso único - não é "usada=true",
  é removida, para nunca ser reaproveitada por engano)

Precisa de migração nova (`pw_migrate create add_e2e_keys --auto ...`) quando
chegarmos à Fase 2.

## Novos endpoints (backend)

- `POST /devices/{device_id}/keys` - o dispositivo publica IK, SPK+assinatura,
  e um lote de OPKs (chamado ao gerar as chaves, e periodicamente para
  repor OPKs gastas)
- `GET /devices/{device_id}/prekey-bundle` - devolve IK+SPK+**uma** OPK de
  alguém (e apaga essa OPK da BD, para não ser reutilizada) - é isto que A
  usa para iniciar sessão com B

## Novos módulos (frontend, `src/crypto/`)

- `primitives.ts` - embrulha as `@noble/*` (dh, hkdfRk, hmacCk, aeadEncrypt,
  aeadDecrypt) - testado sozinho, sem nada do resto do projecto
- `keys.ts` - gera e guarda localmente as chaves privadas (IK, SPK, OPKs);
  publica as públicas no servidor
- `x3dh.ts` - `initiateSession()` (Alice) e `receiveInitialMessage()` (Bob)
- `doubleRatchet.ts` - a máquina de estados: `ratchetEncrypt()`,
  `ratchetDecrypt()`, passo de DH ratchet, gestão de `MKSKIPPED`
- `sessionStore.ts` - persiste o estado da sessão localmente, por par
  (o_meu_device_id, device_id_do_outro) - **não** por conversationId nem por
  userId, porque sessões são por par de dispositivos (liga-se ao gap
  conhecido de multi-dispositivo: por agora cada utilizador só tem um
  dispositivo activo, mas o código já fica correcto para quando isso mudar)

## Onde isto se liga ao que já existe

- O payload do WebSocket passa de `{type: "message", conversation_id, text}`
  para `{type: "message", conversation_id, ciphertext, header}` - o
  `find_recipient_device_ids` no backend não muda nada, continua cego ao
  conteúdo.
- `IdentityContext.sendMessage()` passa a cifrar antes de chamar `send()`;
  `handlePayload()` passa a decifrar antes de guardar em `messages`.
- A persistência local de mensagens (`storage/messageStore.ts`, já feita)
  continua a guardar o **texto decifrado** localmente - cifra é só para o
  transporte, não para o armazenamento no próprio dispositivo.

## Plano de fases

- [ ] **Fase 1 - Primitivos**
  - Instalar `@noble/curves`, `@noble/hashes`, `@noble/ciphers`
  - `src/crypto/primitives.ts` com funções puras: `generateKeyPair()`,
    `dh(privateKey, publicKey)`, `hkdfRk(rk, dhOut)`, `hmacCk(ck)`,
    `aeadEncrypt(key, plaintext, ad)`, `aeadDecrypt(key, ciphertext, ad)`
  - Testes: DH(a,b) == DH(b,a); encrypt→decrypt dá o texto original;
    outputs têm o tamanho certo (32 bytes para chaves, etc.)

- [ ] **Fase 2 - Chaves e publicação**
  - Migração `add_e2e_keys` (campos no `Device` + tabela `OneTimePrekey`)
  - `POST /devices/{id}/keys` e `GET /devices/{id}/prekey-bundle` no backend
  - `src/crypto/keys.ts` - gera as chaves ao criar conta, publica as
    públicas, guarda as privadas em AsyncStorage (nota: sensível - ver se
    vale a pena isolar isto de `messageStore.ts` numa chave própria)

- [ ] **Fase 3 - X3DH**
  - `src/crypto/x3dh.ts` - implementar `initiateSession()` (Alice: busca o
    bundle, faz os 4 DH, deriva SK) e `receiveInitialMessage()` (Bob:
    reconstrói o SK a partir da primeira mensagem recebida)
  - Teste: simular Alice e Bob no mesmo teste, confirmar que chegam ao
    mesmo SK

- [ ] **Fase 4 - Double Ratchet**
  - `src/crypto/doubleRatchet.ts` - estado completo (DHs, DHr, RK, CKs,
    CKr, Ns, Nr, PN, MKSKIPPED) e as quatro operações do spec
  - `src/crypto/sessionStore.ts` - persistir/carregar o estado por par de
    dispositivos
  - Teste: simular uma conversa longa (10+ mensagens), incluindo mensagens
    fora de ordem e uma "perdida" (salta um número), confirmar que decifra
    tudo correctamente nos dois lados

- [ ] **Fase 5 - Ligar ao resto da app**
  - Trocar o payload do WebSocket (texto simples → `{ciphertext, header}`)
  - `IdentityContext`: cifrar em `sendMessage()`, decifrar em
    `handlePayload()`
  - Testar entre duas contas a sério (não só testes automáticos)

## Onde ficámos

Ainda em nenhuma fase - isto é o plano, escrito antes de começar a Fase 1.
Próxima sessão: começar pela **Fase 1** (`src/crypto/primitives.ts`),
instalar as três bibliotecas e escrever os primitivos com testes antes de
tocar em X3DH ou no Double Ratchet propriamente ditos.
