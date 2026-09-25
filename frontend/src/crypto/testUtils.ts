// Só para testes: cria um par de sessões Double Ratchet (Alice, Bob) a
// partir de um X3DH real, como vai acontecer na app.

import { ed25519 } from '@noble/curves/ed25519.js';

import { generateKeyPair } from './primitives';
import { generateDeviceKeys } from './keys';
import { deriveInitiatorSharedKey, deriveResponderSharedKey } from './x3dh';
import {
  type RatchetHeader,
  type RatchetState,
  initAlice,
  initBob,
  ratchetEncrypt,
  ratchetDecrypt,
} from './doubleRatchet';

export interface Party {
  state: RatchetState;
}

export interface Envelope {
  header: RatchetHeader;
  ciphertext: Uint8Array;
}

export function createSessionPair(): { alice: Party; bob: Party } {
  const bobKeys = generateDeviceKeys();
  const opk = bobKeys.oneTimePrekeys[0];
  const { secretKey, publicKey } = ed25519.keygen();

  const x3dh = deriveInitiatorSharedKey({ privateKey: secretKey, publicKey }, generateKeyPair(), {
    identityKey: bobKeys.identityKey.publicKey,
    signedPrekey: bobKeys.signedPrekey.publicKey,
    signedPrekeySignature: bobKeys.signedPrekeySignature,
    signedPrekeyId: bobKeys.signedPrekeyId,
    oneTimePrekey: opk.keyPair.publicKey,
    oneTimePrekeyId: opk.keyId,
  });
  const responder = deriveResponderSharedKey(
    {
      identityKey: bobKeys.identityKey,
      signedPrekeyPrivate: bobKeys.signedPrekey.privateKey,
      oneTimePrekeyPrivate: opk.keyPair.privateKey,
    },
    x3dh.initialMessage,
  );

  return {
    alice: { state: initAlice(x3dh.sharedKey, x3dh.remoteRatchetKey, x3dh.associatedData) },
    bob: { state: initBob(responder.sharedKey, bobKeys.signedPrekey, responder.associatedData) },
  };
}

export function send(party: Party, text: string): Envelope {
  const result = ratchetEncrypt(party.state, new TextEncoder().encode(text));
  party.state = result.state;
  return { header: result.header, ciphertext: result.ciphertext };
}

export function receive(party: Party, envelope: Envelope): string {
  const result = ratchetDecrypt(party.state, envelope.header, envelope.ciphertext);
  party.state = result.state;
  return new TextDecoder().decode(result.plaintext);
}
