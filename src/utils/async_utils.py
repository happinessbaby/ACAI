import asyncio
# import nest_asyncio
# import multiprocessing
import sys
# import trace
import threading
import concurrent.futures
from tenacity import retry, stop_after_delay, retry_if_exception_type
# import time

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

def asyncio_run(coro_factory, as_task=True, timeout=None, max_try=2):
    """
    A better implementation of `asyncio.run` that supports returning values and timeout. 

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    :param timeout: The maximum time to wait for the future (in seconds).
    :return: The result of the future, or raises asyncio.TimeoutError if it times out.
    """

    async def run_with_retries():
      for attempt in range(max_try):
          try:
              result = await asyncio.wait_for(_to_task(coro_factory(), as_task, loop), timeout)
              return result
          except asyncio.TimeoutError:
              if attempt < max_try - 1:
                  print(f"Task timed out after {timeout} seconds. Retrying... ({attempt + 1}/{max_try})")
              else:
                  print(f"Max retries reached. Returning None.")
                  return None
    try:
        loop = asyncio.get_running_loop()
        print("loop exists")
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print('loop is created ')
        # loop.run_until_complete(_to_task(future, as_task, loop))
    try:
        return loop.run_until_complete(run_with_retries())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, asyncio.Task):
        return future
    return loop.create_task(future)


def future_run_with_timeout(run_parser, timeout=10):
    # Use ThreadPoolExecutor to run the function with a timeout
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_parser)
        try:
            # Wait for the function to complete with a timeout
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print("Function timed out")
            return None
        
# Define a retry function with timeout using tenacity
@retry(stop=stop_after_delay(10), retry=retry_if_exception_type(TimeoutError))
def tenacity_run_with_timeout(content_dict, runnable):
    try:
        response = runnable.invoke(content_dict)
        return response
    except Exception as e:
        print(e)
        return None

