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

- [x] **Fase 1 - Primitivos** (completa, commitada)
  - Instalar `@noble/curves`, `@noble/hashes`, `@noble/ciphers`
  - `src/crypto/primitives.ts` com funções puras: `generateKeyPair()`,
    `dh(privateKey, publicKey)`, `hkdfRk(rk, dhOut)`, `hmacCk(ck)`,
    `aeadEncrypt(key, plaintext, ad)`, `aeadDecrypt(key, ciphertext, ad)`
  - Testes: DH(a,b) == DH(b,a); encrypt→decrypt dá o texto original;
    outputs têm o tamanho certo (32 bytes para chaves, etc.)
  - Decisões tomadas pelo caminho: Vitest (não `jest-expo`) para lógica
    pura sem RN, por ser ESM nativo e não precisar do
    `transformIgnorePatterns` que o `jest-expo` exigiria para os
    `@noble/*`; Node do projecto migrado para 24 via `.nvmrc`
    (`frontend/.nvmrc`, `nvm use`), independente do Node global da
    máquina, para poder usar o Vitest mais recente.

- [x] **Fase 2 - Chaves e publicação** (completa, testada, **commitada**)
  - Migração `004_add_e2e_keys` (campos no `Device` + tabela
    `OneTimePrekey`) - já corrida contra a BD de dev
  - `POST /devices/{id}/keys` e `GET /devices/{id}/prekey-bundle` no
    backend (`app/api/devices.py` + `app/services/keys.py`) -
    `pytest -q`: 5 passed
  - `src/crypto/keys.ts` - gera as chaves ao criar conta (chamado em
    `register()`/`login()` do `IdentityContext`, nunca em
    `resumeSession()` - cada login novo já cria um `Device` novo, ver
    limitação conhecida em `projeto-chat-selfhosted.yaml`), publica as
    públicas, guarda as privadas em AsyncStorage
  - `src/crypto/encoding.ts` - base64 ↔ Uint8Array escrito à mão (sem
    `Buffer`/`atob`/`btoa`, indisponíveis no Hermes/RN, sem nova
    dependência)
  - Decisões tomadas pelo caminho, que desviam ligeiramente do desenho
    original acima:
    - **`POST /devices/{id}/keys` verifica `client_token`** contra o
      `Device` (403 se não bater, 404 se o device não existir) - sem
      isto, qualquer um podia publicar chaves falsas para o `device_id`
      de outra pessoa e quebrar a autenticidade da cifra na raiz (nenhum
      outro endpoint desta API verifica dono nenhum, mas este caso era
      grave demais para herdar essa simplificação)
    - **`key_id` das OPKs é aleatório** (32 bits), não uma sequência
      `1..N` reiniciada a cada chamada - e `storeDeviceKeys()` faz
      *merge* com as OPKs já guardadas localmente em vez de as substituir.
      Prepara o terreno para uma futura reposição periódica de OPKs (ainda
      não construída) sem perder chaves privadas de OPKs antigas ainda por
      consumir
    - Removido o campo morto `User.identity_public_key` (nunca chegou a
      ser usado - a chave de identidade vive no `Device`, como este plano
      sempre disse)
  - **Nota para a Fase 5:** como `find_recipient_device_ids` já devolve
    todos os dispositivos activos de um utilizador, uma vez a cifra ligada
    ao envio de mensagens, quem envia terá de cifrar **uma vez por
    dispositivo destinatário**, não uma vez por conversa - relevante assim
    que multi-dispositivo deixar de ser "um só dispositivo por utilizador"
  - **Teste manual confirmado (2026-09-25):** conta criada com
    backend (`--host 0.0.0.0`, exposto na LAN) + frontend a correr; no
    Postgres, o `Device` ficou com `identity_key`/`signed_prekey`
    preenchidos e exactamente 20 linhas em `one_time_prekeys`; duas
    chamadas seguidas a `GET /devices/{id}/prekey-bundle` devolveram
    `one_time_prekey_id` diferentes (233364501, depois 288622942) e a
    contagem de OPKs desceu de 20 para 18, confirmando que cada OPK é
    consumida uma única vez, sem reutilização
  - **Gap identificado, não bloqueia a Fase 3:** quando as OPKs de um
    device se esgotam, `get_prekey_bundle()` devolve o bundle na mesma
    mas com `one_time_prekey_id`/`one_time_prekey` a `null` - válido
    segundo a spec do X3DH (OPK é opcional, cai-se para 3 DH em vez de
    4). Não existe ainda nenhum mecanismo que reponha OPKs
    automaticamente quando ficam poucas - fica para uma fase futura,
    fora do âmbito da Fase 3/4/5

- [x] **Fase 3 - X3DH** (completa, testada, commitada)
  - `src/crypto/x3dh.ts` - `initiateSession()` (Alice) e
    `receiveInitialMessage()` (Bob), separados em núcleo puro
    (`deriveInitiatorSharedKey`/`deriveResponderSharedKey`, sem I/O,
    testado directamente) + wrappers de I/O finos por cima
  - Testes em `x3dh.test.ts`: Alice e Bob chegam à mesma SK, com OPK e sem
    (pool esgotado); SK com/sem OPK são diferentes (DH4 participa mesmo);
    assinatura da SPK adulterada é rejeitada; OPK referida mas já
    consumida é rejeitada; sessões diferentes dão SKs diferentes; e um
    teste de integração dos wrappers via `initiateSession`/
    `receiveInitialMessage` com AsyncStorage e API mockados
  - Decisões tomadas pelo caminho:
    - **A IK é Ed25519** (decisão já tomada na Fase 2, reutilizada para
      assinar a SPK), mas o X3DH precisa de X25519 para o DH. Resolvido
      com a conversão birracional Edwards→Montgomery que o
      `@noble/curves` já expõe (`ed25519.utils.toMontgomery` /
      `toMontgomerySecret`) - novos primitivos `edPublicKeyToX25519` /
      `edPrivateKeyToX25519` em `primitives.ts`
    - **Prefixo `F`** (32 bytes `0xFF`) antes dos DHs concatenados no KDF,
      tal como a spec do X3DH recomenda especificamente para o caso de a
      identity key ser reutilizada fora do DH (aqui: para assinar a SPK)
    - Novo primitivo `kdfX3dh` em `primitives.ts` (HKDF-SHA256, salt fixo
      de zeros, info próprio) - distinto de `hkdfRk`, que é específico do
      Double Ratchet (1 DH de entrada, 2 saídas)
    - `deriveInitiatorSharedKey` verifica sempre a assinatura da SPK de
      Bob antes de fazer qualquer DH (`SignedPrekeySignatureError` se
      falhar) - sem isto um servidor comprometido podia trocar a SPK e
      fazer MITM
    - `consumeOneTimePrekey` novo em `keys.ts` (lê + apaga a privada da
      OPK usada do storage local) - preenche o gap que a própria Fase 2
      já tinha deixado assinalado em comentário
    - `fetchPrekeyBundle` novo em `api/devices.ts` - sem alterações ao
      backend, o endpoint da Fase 2 já devolve tudo o que é preciso

- [x] **Fase 4 - Double Ratchet** (completa, testada, commitada)
  - `src/crypto/doubleRatchet.ts` - estado completo (DHs, DHr, RK, CKs,
    CKr, Ns, Nr, PN, MKSKIPPED) e as operações da spec (`initAlice`,
    `initBob`, `ratchetEncrypt`, `ratchetDecrypt`, com
    TrySkippedMessageKeys, SkipMessageKeys e DHRatchet internos)
  - `src/crypto/sessionStore.ts` - `saveSession`/`loadSession`/
    `deleteSession` por par de dispositivos (chave
    `whattspoppin.session.<meu>.<outro>`), JSON com base64
  - Testes (`doubleRatchet.test.ts`, `sessionStore.test.ts`, sessões
    criadas a partir de um X3DH real via `testUtils.ts`): conversa de 13
    mensagens alternadas e em rajadas; fora de ordem na mesma cadeia e
    entre passos de DH; mensagem perdida; replay rejeitado; ciphertext e
    cabeçalho adulterados rejeitados sem estragar o estado; MAX_SKIP;
    round-trip do estado guardado com chaves saltadas e conversa a
    continuar depois de recarregar
  - Decisões tomadas pelo caminho:
    - **Estado imutável**: cada operação devolve um estado novo em vez de
      mutar - se a decifra falhar, o estado anterior fica intacto (a spec
      exige descartar alterações em caso de erro). Quem chama só persiste
      depois de sucesso
    - **O par ratchet inicial de Bob é a signed prekey dele**, como a
      spec manda - `X3dhInitiatorResult` passou a expor
      `remoteRatchetKey` (SPK de Bob) e `associatedData`, e
      `deriveResponderSharedKey`/`receiveInitialMessage` passaram a
      devolver `{ sharedKey, associatedData }`
    - **AD = IK_A || IK_B** (do X3DH), e o AD de cada mensagem é
      `AD || encodeHeader(header)` - cabeçalho com tamanho fixo de 40
      bytes (dh 32 + pn 4 + n 4, big-endian), por isso adulterar o
      cabeçalho faz a decifra falhar
    - `MAX_SKIP = 1000` por cadeia; contadores do cabeçalho validados
      (inteiros entre 0 e 2^32-1)
  - **Nota para a Fase 5:** a SPK é também o primeiro par ratchet de Bob,
    por isso uma futura rotação de SPK tem de manter a privada antiga até
    as sessões que dela dependem terem avançado. Também ainda não há
    limite global ao tamanho de MKSKIPPED (a spec sugere apagar chaves
    saltadas antigas ao fim de algum tempo/número) - fica para quando
    houver tráfego real

- [x] **Fase 5 - Ligar ao resto da app** (código e testes automáticos
  feitos; **falta o `pytest` na BD de teste e o teste manual**; por commitar)
  - **BD de teste isolada:** `backend/tests/conftest.py` força o `pytest` a
    usar `TEST_DATABASE_URL` e aborta se não existir ou se o nome da BD não
    acabar em `_test`. Corre as migrações e faz `TRUNCATE` no início de cada
    execução. Criar a BD:
    `docker exec -it whattspoppin-postgres createdb -U whattspoppin whattspoppin_test`
    e copiar `TEST_DATABASE_URL` do `.env.example` para o `.env`
  - **Protocolo do WebSocket:** o cliente manda
    `{conversation_id, envelopes: [{device_id, header, ciphertext, x3dh}]}`,
    um envelope por dispositivo destinatário. O servidor entrega a cada device
    só o seu envelope, com `sender_device_id` tirado da ligação (nunca do
    cliente). Descarta envelopes para devices que não são participantes da
    conversa e ignora payloads mal formados. Nunca vê texto
  - **Endpoint novo:** `GET /conversations/{id}/devices?device_id=<o meu>`
    devolve os devices dos outros participantes que estão activos e com
    chaves publicadas
  - **`crypto/messaging.ts`:** `encryptForConversation` e `decryptIncoming`,
    ambos numa fila em série, porque cada operação lê e grava a sessão e duas
    em paralelo perderiam uma escrita. A fila também preserva a ordem do
    WebSocket
  - **Prelúdio X3DH repetido:** Alice põe o prelúdio em todas as mensagens
    até decifrar a primeira resposta de Bob, como o Signal recomenda. Assim,
    se a primeira mensagem se perder, a seguinte ainda abre a sessão. Bob
    distingue "prelúdio repetido" de "sessão nova" pela EK de Alice, guardada
    no `SessionRecord`
  - **A OPK só é gasta depois de a primeira mensagem decifrar:**
    `receiveInitialMessage` ganhou `consumeOneTimePrekey: false`, para uma
    mensagem adulterada não queimar a OPK e impedir a legítima de abrir a
    sessão
  - **`IdentityContext`:** a mensagem aparece logo no ecrã de quem envia e é
    cifrada e enviada em segundo plano. Uma mensagem que não decifra aparece
    como `[mensagem não pôde ser decifrada]` e gera um `console.warn`
  - Testes: `messaging.test.ts` (8 testes, entre dispositivos simulados) e
    `backend/tests/test_messaging.py` (endpoint, routing por device,
    descarte de envelopes fora da conversa, payloads mal formados)
  - **Limitações conhecidas, que ficam para depois:**
    - *Inícios simultâneos:* se A e B abrirem sessão um com o outro ao mesmo
      tempo, a última sessão recebida substitui a outra, e as mensagens que se
      cruzarem podem não decifrar. O Signal resolve isto com um arquivo de
      sessões
    - *Devices antigos:* cada login cria um device novo e os antigos
      continuam activos com chaves. Quem envia cifra também para eles e
      gasta-lhes OPKs. É o gap de multi-dispositivo que já estava registado
    - *Entrega não confirmada:* se nenhum device do destinatário tiver
      chaves, a mensagem aparece como enviada mas não chega a ninguém (só há
      um `console.warn`)
    - *Grupos:* cifrar por device é o normal em 1:1. Para grupos, o plano é
      Sender Keys (ver `esquema_de_grupos` no yaml), e para grupos muito
      grandes existe o MLS (RFC 9420)

## Onde ficámos

**Estado em 2026-09-25:** Fases 1 a 5 completas no código. `npm run test`
(77 testes), `npx tsc --noEmit` e `npx expo lint` limpos no frontend;
`ruff` e `mypy` limpos no backend. **Falta:**
1. criar a BD `whattspoppin_test`, pôr `TEST_DATABASE_URL` no `.env` e
   correr `pytest -q`
2. teste manual com duas contas novas, confirmando no separador Network → WS
   do browser que os frames só levam `ciphertext` e `header`
3. commitar a Fase 5

Depois disso a cifra ponta-a-ponta do MVP (1:1) está completa. O
`README.md` e o `projeto-chat-selfhosted.yaml` ainda dizem "sem cifra" e
têm de ser actualizados.
