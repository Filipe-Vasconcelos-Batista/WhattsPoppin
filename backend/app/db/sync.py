from collections.abc import Callable

from starlette.concurrency import run_in_threadpool

from app.db import db


def _call_with_connection[T](func: Callable[..., T], *args: object) -> T:
    with db.connection_context():
        return func(*args)


async def run_sync[T](func: Callable[..., T], *args: object) -> T:
    return await run_in_threadpool(_call_with_connection, func, *args)
