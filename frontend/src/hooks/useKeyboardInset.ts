import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

/** Só web - altura do teclado do telemóvel em pixels (0 quando fechado).
 * Vem do visualViewport do browser, que é a única API que sabe realmente
 * quanto espaço o teclado ocupa (window.innerHeight não muda em vários
 * browsers móveis). Usa-se para empurrar um elemento para cima do teclado,
 * sem mexer no resto do ecrã. */
export function useKeyboardInset(): number {
  const [inset, setInset] = useState(0);

  useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined') return;

    const viewport = window.visualViewport;
    if (!viewport) return;

    function update() {
      const keyboardHeight = window.innerHeight - viewport!.height - viewport!.offsetTop;
      setInset(Math.max(0, Math.round(keyboardHeight)));
    }

    update();
    viewport.addEventListener('resize', update);
    viewport.addEventListener('scroll', update);
    return () => {
      viewport.removeEventListener('resize', update);
      viewport.removeEventListener('scroll', update);
    };
  }, []);

  return inset;
}
