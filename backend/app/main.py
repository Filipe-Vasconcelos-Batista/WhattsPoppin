"""Ponto de entrada da API. Ver projeto-chat-selfhosted.yaml na raiz do
repositório para o desenho completo (federação, cifra, retenção, etc.)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.conversations import router as conversations_router
from app.api.identity import router as identity_router
from app.api.ws import router as ws_router

app = FastAPI(title="WatsPoppin", version="0.0.1")

# MVP local: frontend corre noutra porta (Expo web). Sem cifra ainda, tudo
# em localhost - apertar isto é trabalho para quando isto sair de casa.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(identity_router)
app.include_router(conversations_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
