// Testa o Double Ratchet sobre sessões criadas por um X3DH real: conversa
// longa, mensagens fora de ordem, perdidas, repetidas e adulteradas.

import { describe, it, expect } from 'vitest';

import { MAX_SKIP, encodeHeader, ratchetEncrypt } from './doubleRatchet';
import { createSessionPair, send, receive, type Envelope } from './testUtils';

describe('Double Ratchet', () => {
  it('conversa longa com vez alternada e rajadas decifra tudo dos dois lados', () => {
    const { alice, bob } = createSessionPair();
    const script: ['A' | 'B', string][] = [
      ['A', 'olá bob'],
      ['A', 'estás aí?'],
      ['B', 'sim, diz'],
      ['A', 'isto já é cifrado'],
      ['B', 'boa'],
      ['B', 'e cada mensagem tem chave própria'],
      ['B', 'forward secrecy'],
      ['A', 'e o DH roda quando muda a vez'],
      ['B', 'exacto'],
      ['A', 'mensagem 10'],
      ['A', 'mensagem 11'],
      ['A', 'mensagem 12'],
      ['B', 'fim'],
    ];

    for (const [from, text] of script) {
      const [sender, recipient] = from === 'A' ? [alice, bob] : [bob, alice];
      expect(receive(recipient, send(sender, text))).toBe(text);
    }
  });

  it('decifra mensagens fora de ordem dentro da mesma cadeia', () => {
    const { alice, bob } = createSessionPair();
    const m1 = send(alice, 'um');
    const m2 = send(alice, 'dois');
    const m3 = send(alice, 'três');

    expect(receive(bob, m3)).toBe('três');
    expect(receive(bob, m1)).toBe('um');
    expect(receive(bob, m2)).toBe('dois');
    expect(bob.state.skipped.size).toBe(0);
  });

  it('decifra uma mensagem atrasada de uma cadeia anterior depois de um passo de DH', () => {
    const { alice, bob } = createSessionPair();
    const a1 = send(alice, 'a1');
    const a2 = send(alice, 'a2');
    expect(receive(bob, a1)).toBe('a1');

    expect(receive(alice, send(bob, 'b1'))).toBe('b1');

    const a3 = send(alice, 'a3'); // já com chave ratchet nova, pn = 2
    expect(a3.header.pn).toBe(2);
    expect(receive(bob, a3)).toBe('a3');
    expect(receive(bob, a2)).toBe('a2');
  });

  it('uma mensagem perdida não impede as seguintes', () => {
    const { alice, bob } = createSessionPair();
    const m1 = send(alice, 'um');
    send(alice, 'perdida'); // nunca chega
    const m3 = send(alice, 'três');

    expect(receive(bob, m1)).toBe('um');
    expect(receive(bob, m3)).toBe('três');
    expect(bob.state.skipped.size).toBe(1);
    expect(receive(alice, send(bob, 'resposta'))).toBe('resposta');
  });

  it('rejeita replay de uma mensagem já decifrada (normal e saltada)', () => {
    const { alice, bob } = createSessionPair();
    const m1 = send(alice, 'um');
    const m2 = send(alice, 'dois');

    receive(bob, m2);
    expect(() => receive(bob, m2)).toThrow();

    receive(bob, m1); // vem das chaves saltadas
    expect(() => receive(bob, m1)).toThrow();
  });

  it('rejeita ciphertext adulterado sem estragar o estado', () => {
    const { alice, bob } = createSessionPair();
    const message = send(alice, 'intacta');
    const tampered = message.ciphertext.slice();
    tampered[tampered.length - 1] ^= 0xff;

    expect(() => receive(bob, { header: message.header, ciphertext: tampered })).toThrow();
    expect(receive(bob, message)).toBe('intacta');
  });

  it('rejeita cabeçalho adulterado sem estragar o estado', () => {
    const { alice, bob } = createSessionPair();
    receive(bob, send(alice, 'primeira'));
    const message = send(alice, 'segunda');

    const tamperedPn: Envelope = { ...message, header: { ...message.header, pn: message.header.pn + 1 } };
    const tamperedN: Envelope = { ...message, header: { ...message.header, n: message.header.n + 1 } };

    expect(() => receive(bob, tamperedPn)).toThrow();
    expect(() => receive(bob, tamperedN)).toThrow();
    expect(receive(bob, message)).toBe('segunda');
  });

  it(`rejeita saltar mais de ${MAX_SKIP} mensagens`, () => {
    const { alice, bob } = createSessionPair();
    const message = send(alice, 'x');
    const huge: Envelope = { ...message, header: { ...message.header, n: MAX_SKIP + 1 } };

    expect(() => receive(bob, huge)).toThrow(/Demasiadas mensagens saltadas/);
  });

  it('rejeita contadores inválidos no cabeçalho', () => {
    const { alice, bob } = createSessionPair();
    const message = send(alice, 'x');

    expect(() => receive(bob, { ...message, header: { ...message.header, n: -1 } })).toThrow();
    expect(() => receive(bob, { ...message, header: { ...message.header, n: 1.5 } })).toThrow();
  });

  it('o mesmo texto dá ciphertexts diferentes (chave por mensagem)', () => {
    const { alice } = createSessionPair();
    const first = send(alice, 'igual');
    const second = send(alice, 'igual');
    expect(first.ciphertext).not.toEqual(second.ciphertext);
  });

  it('Bob não consegue enviar antes de receber a primeira mensagem', () => {
    const { bob } = createSessionPair();
    expect(() => ratchetEncrypt(bob.state, new Uint8Array([1]))).toThrow();
  });

  it('encodeHeader tem 40 bytes e codifica os contadores em big-endian', () => {
    const header = { dh: new Uint8Array(32).fill(7), pn: 1, n: 258 };
    const encoded = encodeHeader(header);
    expect(encoded.length).toBe(40);
    expect([...encoded.slice(32)]).toEqual([0, 0, 0, 1, 0, 0, 1, 2]);
  });
});
