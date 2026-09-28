import Constants from 'expo-constants';

const DEFAULT_API_PORT = 8000;

const API_PORT_BY_WEB_PORT: Record<string, number> = {
  '8091': 8001,
  '8092': 8002,
};

function apiUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) return process.env.EXPO_PUBLIC_API_URL;

  if (typeof window !== 'undefined' && window.location?.hostname) {
    const port = API_PORT_BY_WEB_PORT[window.location.port] ?? DEFAULT_API_PORT;
    return `http://${window.location.hostname}:${port}`;
  }

  // App nativa em dev: o backend corre na mesma máquina que o servidor do Expo.
  const devServerHost = Constants.expoConfig?.hostUri?.split(':')[0] ?? 'localhost';
  return `http://${devServerHost}:${DEFAULT_API_PORT}`;
}

export const API_URL = apiUrl();
export const WS_URL = API_URL.replace(/^http/, 'ws');
