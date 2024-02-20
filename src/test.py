import asyncio

class YourDataProcessor():
    def __init__(self, data_queue=None, data_queue2=None, event_loop=None):
        self.data_queue = data_queue
        self.event_loop = event_loop
        # self.task = asyncio.ensure_future(self.process_data())

    async def process_data(self, conn):

        while True:
            data = await self.data_queue.get()
            # Process the data as needed
            print("Processing data:", data)
