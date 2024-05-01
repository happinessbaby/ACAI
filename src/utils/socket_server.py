import asyncio
import websockets
import json
import threading
# from six.moves import queue
import queue
from google.cloud import speech
from google.cloud.speech_v1 import types
from utils.async_utils import asyncio_run
from google.oauth2 import service_account
import functools




# IP = '0.0.0.0'
# PORT = 8000
# data_queue = asyncio.Queue()

# Specify the correct path and filename
json_file_path = '/home/tebblespc/acai-412122-66efa5504060.json'

# Authenticate using the service account key file
credentials = service_account.Credentials.from_service_account_file(json_file_path)

class Transcoder():
    """
    Converts audio chunks to text
    """
    def __init__(self, encoding, rate, language):
        self.buff = queue.Queue()
        self.encoding = encoding
        self.language = language
        self.rate = rate
        # self.closed = True
        self.closed_event = threading.Event()  # Event to signal when to stop the stream
        self.transcript = ""
        # self.loop = asyncio.get_event_loop()

    def start(self):
        """Start up streaming speech call.
        
        Note: self.process cannot be blocking since there's still code that comes after the call in AudioProcessor.
        
        """
        print("started Transcoder")
        threading.Thread(target=self.process, daemon=True).start()
        # self.loop.run_in_executor(None, self.process)


    def response_loop(self, responses):
        """
        Pick up the final result of Speech to text conversion
        """
        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            transcript = result.alternatives[0].transcript
            if result.is_final:
                self.transcript += transcript

    def process(self):
        """
        Audio stream recognition and result parsing
        """
        #You can add speech contexts for better recognition
        # cap_speech_context = types.SpeechContext(phrases=["Add your phrases here"])
        try:
            while not self.closed_event.is_set():
                client = speech.SpeechClient(credentials=credentials)
                config = types.RecognitionConfig(
                    encoding=self.encoding,
                    sample_rate_hertz=self.rate,
                    language_code=self.language,
                    # speech_contexts=[cap_speech_context,],
                    model='command_and_search'
                )
                streaming_config = types.StreamingRecognitionConfig(
                    config=config,
                    interim_results=False,
                    single_utterance=False,
                    enable_voice_activity_events=True,
                    )
                audio_generator = self.stream_generator()
                requests = (types.StreamingRecognizeRequest(audio_content=content)
                            for content in audio_generator)
                responses = client.streaming_recognize(streaming_config, requests)
                self.response_loop(responses)
        except Exception as e:
            print(e)
        finally:
            self.process()
            print("Restarting audio processing loop")
            # Optionally, you can handle any cleanup or finalize tasks here
      

    def stream_generator(self):
        while not self.closed_event.is_set():
            chunk = self.buff.get()
            # print(f"CHUNK: {chunk}")
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self.buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b''.join(data)


    def write(self, data):
        """
        Writes data to the buffer
        """
        self.buff.put(data)

    def stop(self):
        self.closed_event.set()  # Set the event to signal the stream to stop

class SocketServer():

    def __init__(self, ip="0.0.0.0", port=8000):
        self.IP= ip
        self.PORT = port
        self.data_queue = asyncio.Queue()

    async def _init_socket_server(self, ):

        try:
            socket_server = websockets.serve(self.audio_processor, self.IP, self.PORT)
             # WebSocket server runs on the main thread
            asyncio_run(socket_server, as_task=False)
        except OSError as e:
            print("Socket server already exists")
        ## address already in use error
            pass 
        except Exception as e:
            self._init_socket_server()

    async def audio_processor(self, websocket, path, ):
        """
        Collects audio from the stream, writes it to buffer and return the output of Google speech to text
        """
        config = await websocket.recv()
        if not isinstance(config, str):
            print("ERROR, no config")
            return
        else:
            print("CONFIG RECEIVE:", config)
        config = json.loads(config)
        transcoder = Transcoder(
            encoding=config["format"],
            rate=config["rate"],
            language=config["language"]
        )
        transcoder.start()
        while True:
            try:
                # while True:
                data = await websocket.recv()
                asyncio.create_task(self.process_data(transcoder, data, websocket))
            except websockets.ConnectionClosed:
                print("Connection closed")
                await asyncio.sleep(1)  # Adjust the delay as needed

    async def process_data(self, transcoder, data, websocket):
        if isinstance(data, (bytes, bytearray)):
            transcoder.write(data)
            transcoder.closed_event.clear()
        else:
            try:
                data = json.loads(data)
                # when user stopped recording, send transcript to AI
                if data.get('action', None) == 'stopRecording':
                    if transcoder.transcript:
                        print(transcoder.transcript)
                        await websocket.send(f"200:{transcoder.transcript}")
                        print(f"transcript sent from socket")
                        await self.data_queue.put(transcoder.transcript)
                        print(f"transcript sent to data queue")
                        transcoder.transcript = ""
                if data.get('action', None)== 'userUpload':
                    upload = data.get('upload', None)
                    if upload:
                        await websocket.send(f"201:upload")
                        print("user upload sent from socket server")
                        await self.data_queue.put(upload)
                        print("user upload sent to data queue")
                if data.get('action', None)=="endInterview":
                    await websocket.send("202:end")
                    print("user ends interview")
                    await self.data_queue.put("END")
            except json.JSONDecodeError as e:
                raise 


    
        

    # def run(self):
    #     self._initialize_socket()
    #     try:
    #         asyncio.get_event_loop().run_forever()
    #     except KeyboardInterrupt:
    #         print("Shutting down the server...")
    #     finally:
    #         asyncio.get_event_loop().close()




