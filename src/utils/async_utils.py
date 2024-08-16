import asyncio
import nest_asyncio
import multiprocessing
import sys
# import trace
import threading
import time

class thread_with_trace(threading.Thread):
  def __init__(self, *args, **keywords):
    threading.Thread.__init__(self, *args, **keywords)
    self.killed = False

  def start(self):
    self.__run_backup = self.run
    self.run = self.__run      
    threading.Thread.start(self)

  def __run(self):
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup

  def globaltrace(self, frame, event, arg):
    if event == 'call':
      return self.localtrace
    else:
      return None

  def localtrace(self, frame, event, arg):
    if self.killed:
      if event == 'line':
        raise SystemExit()
    return self.localtrace

  def kill(self):
    self.killed = True

def asyncio_run(future, as_task=True, timeout=None):
    """
    A better implementation of `asyncio.run` that supports returning values and timeout. 

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    :param timeout: The maximum time to wait for the future (in seconds).
    :return: The result of the future, or raises asyncio.TimeoutError if it times out.
    """

    try:
        loop = asyncio.get_running_loop()
        print("loop exists")
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print('loop is created ')
        # loop.run_until_complete(_to_task(future, as_task, loop))
    try:
        return loop.run_until_complete(asyncio.wait_for(_to_task(future, as_task, loop), timeout))
    except asyncio.TimeoutError:
        print(f"Task timed out after {timeout} seconds.")
        return None  # Handle the timeout case appropriately (e.g., return a default value or raise an exception)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, asyncio.Task):
        return future
    return loop.create_task(future)



    # else:
    #     nest_asyncio.apply(loop)
    # finally:
    #     loop.run_until_complete(_to_task(future, as_task, loop))
        # loop.close()
        
        # return asyncio.run(_to_task(future, as_task, loop))
