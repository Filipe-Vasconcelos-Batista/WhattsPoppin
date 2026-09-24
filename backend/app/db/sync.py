from collections.abc import Callable

from starlette.concurrency import run_in_threadpool


async def run_sync[T](func: Callable[..., T], *args: object) -> T:
    return await run_in_threadpool(func, *args)
