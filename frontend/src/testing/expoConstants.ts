// Substitui o expo-constants nos testes (ver vitest.config.mts): o verdadeiro
// importa o react-native, que o Vitest não consegue ler (Flow).
const Constants: { expoConfig: { hostUri?: string } | null } = { expoConfig: null };

export default Constants;
