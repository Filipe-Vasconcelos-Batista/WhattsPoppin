import { useEffect, useState } from 'react';
import { AppState, Platform } from 'react-native';

// "A pessoa está mesmo a ver a app": na web, aba visível E janela com foco
// (como o WhatsApp Web); no nativo, app em primeiro plano.
function isWebActive(): boolean {
  if (typeof document === 'undefined') return false;
  return document.visibilityState === 'visible' && document.hasFocus();
}

function currentlyActive(): boolean {
  return Platform.OS === 'web' ? isWebActive() : AppState.currentState === 'active';
}

export function useIsAppActive(): boolean {
  const [active, setActive] = useState(currentlyActive);

  useEffect(() => {
    if (Platform.OS === 'web') {
      const update = () => setActive(isWebActive());
      document.addEventListener('visibilitychange', update);
      window.addEventListener('focus', update);
      window.addEventListener('blur', update);
      update();
      return () => {
        document.removeEventListener('visibilitychange', update);
        window.removeEventListener('focus', update);
        window.removeEventListener('blur', update);
      };
    }

    const subscription = AppState.addEventListener('change', (state) =>
      setActive(state === 'active'),
    );
    return () => subscription.remove();
  }, []);

  return active;
}
