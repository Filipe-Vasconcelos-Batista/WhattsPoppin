"""Ponto de entrada da API. Ver projeto-chat-selfhosted.yaml na raiz do
repositório para o desenho completo (federação, cifra, retenção, etc.)."""

from fastapi import FastAPI

app = FastAPI(title="WatsPoppin", version="0.0.1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
