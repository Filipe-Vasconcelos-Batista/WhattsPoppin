from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.contacts import router as contacts_router
from app.api.conversations import router as conversations_router
from app.api.devices import router as devices_router
from app.api.users import router as users_router
from app.api.ws import router as ws_router
from app.federation.keys import signing_key
from app.federation.routes import router as federation_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    signing_key()
    yield


app = FastAPI(title="WatsPoppin", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(contacts_router)
app.include_router(conversations_router)
app.include_router(devices_router)
app.include_router(federation_router)
app.include_router(users_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
