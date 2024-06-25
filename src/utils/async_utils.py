import asyncio
import nest_asyncio
import multiprocessing


def asyncio_run(future, as_task=True):
    """
    A better implementation of `asyncio.run`.

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """

    try:
        loop = asyncio.get_running_loop()
        print("loop exists")
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        print('loop is created ')
        # loop.run_until_complete(_to_task(future, as_task, loop))

    else:
        nest_asyncio.apply(loop)
    finally:
        loop.run_until_complete(_to_task(future, as_task, loop))
        # loop.close()
        
        # return asyncio.run(_to_task(future, as_task, loop))


def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, asyncio.Task):
        return future
    return loop.create_task(future)


