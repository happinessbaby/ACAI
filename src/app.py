import asyncio
import nest_asyncio
import streamlit as st
from backend.socket import Socket
# from streamlit_interviewbot import Interview
from test import YourDataProcessor
import multiprocessing as mp




if __name__ == '__main__':

    conn1, conn2 = mp.Pipe()
    web_socket_server = Socket()
    process_1 = mp.Process(target=web_socket_server._initialize_socket, args=(conn1, ))
    test = YourDataProcessor(data_queue=web_socket_server.data_queue)
    process_2 = mp.Process(target=test.process_data, args=(conn2,))
    process_1.start()
    process_2.start()
    process_1.join()
    process_2.join()


    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    nest_asyncio.apply()
    web_socket_server = Socket()
    # interviewer = Interview(data_queue=web_socket_server.data_queue)
    test = YourDataProcessor(data_queue=web_socket_server.data_queue)

    tasks = [
        asyncio.ensure_future(web_socket_server._initialize_socket()),
        # asyncio.ensure_future(interviewer.receive_transcript()),
        asyncio.ensure_future(test.process_data()),
    ]

    event_loop.run_until_complete(asyncio.gather(*tasks))