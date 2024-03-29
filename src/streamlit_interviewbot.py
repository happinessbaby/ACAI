import streamlit as st
from streamlit_chat import message
from streamlit_extras.add_vertical_space import add_vertical_space
from pathlib import Path
import random
import time
import openai
import os
import uuid
from io import StringIO
from langchain.agents import AgentType, Tool, load_tools
from langchain.callbacks import StreamlitCallbackHandler
from backend.career_advisor import ChatController
from backend.mock_interviewer import InterviewController
from callbacks.capturing_callback_handler import playback_callbacks
from utils.basic_utils import convert_to_txt, read_txt, retrieve_web_content, html_to_text, delete_file, mk_dirs, write_file, read_file
from utils.openai_api import check_content_safety, get_completion
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  check_content, get_generated_responses, get_web_resources
import asyncio
import concurrent.futures
import subprocess
import sys
from multiprocessing import Process, Queue, Value
import pickle
import requests
import functools
from typing import Any
import multiprocessing as mp
from langchain.embeddings import OpenAIEmbeddings
from utils.langchain_utils import update_vectorstore
from pynput.keyboard import Key, Controller
from pynput import keyboard
import sounddevice as sd
from sounddevice import CallbackFlags
import soundfile as sf
import numpy  as np# Make sure NumPy is loaded before it is used in the callback
assert np  # avoid "imported but unused" message (W0611)
import tempfile
import openai
# from elevenlabs import generate, play, set_api_key
from time import gmtime, strftime
import playsound
from streamlit_modal import Modal
import json
from threading import Thread
from langchain.tools import ElevenLabsText2SpeechTool, GoogleCloudTextToSpeechTool
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import re
import base64
from botocore.errorfactory import ClientError
import boto3
import botocore
from botocore.errorfactory import ClientError
from cookie_manager import get_cookie, get_all_cookies
from dynamodb_utils import create_table, retrieve_sessions, save_current_conversation, check_attribute_exists, save_user_info, init_table
from aws_manager import get_aws_session, request_aws4auth
import pywinctl as pwc
from my_component import my_component
from google.cloud import texttospeech
from pydub import AudioSegment
import io
import wave
from audio_recorder_streamlit import audio_recorder
from st_audiorec import st_audiorec
from streamlit_mic_recorder import mic_recorder,speech_to_text
from speech_recognition import Recognizer, AudioData
import asyncio
import websockets
import json
import threading
# from six.moves import queue
import queue
from google.cloud import speech
from backend.socket_server import SocketServer, Transcoder
from utils.async_utils import asyncio_run
import nest_asyncio
import websocket
import streamlit.components.v1 as components

# from test import YourDataProcessor



_ = load_dotenv(find_dotenv()) # read local .env file
st.set_page_config(layout="wide")
openai.api_key = os.environ['OPENAI_API_KEY']
STORAGE = os.environ['STORAGE']
user_vs_name = os.environ["USER_INTERVIEW_VS_NAME"]
png_file = os.environ["INTERVIEW_BG"]
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="/home/tebblespc/Documents/acai-412122-dd69ac33da42.json"
placeholder = st.empty()
# sd.default.samplerate=48000
# sd.default.channels = 1, 2
# sd.default.device = 1
# duration = 600 # duration of each recording in seconds
# fs = 44100 # sample rate
# channels = 1 # number of channel
# # COMBINATION = {keyboard.Key.r, keyboard.Key.ctrl}
# device = 4
# keyboard = Controller()
# keyboard_event = Keyboard()
uri = "ws://127.0.0.1:8765"




class Interview():


    # COMBINATION = [{keyboard.KeyCode.from_char('r'), keyboard.Key.space}, {keyboard.Key.shift, keyboard.Key.esc}, {keyboard.Key.enter}]
    ctx = get_script_run_ctx()
    # currently_pressed = set()
    # q = queue.Queue()
    ai_col, human_col = st.columns(2, gap="large")
    cookie = get_cookie("userInfo")
    aws_session = get_aws_session()

    

    def __init__(self, data_queue, socket_client):
        if self.cookie:
            # self.userId = self.cookie.split("###")[1]
            self.userId = re.split("###|@", self.cookie)[1]
            print(self.userId)
        else:
            self.userId = None
        if "interview_sessionId" not in st.session_state:
            st.session_state["interview_sessionId"] = str(uuid.uuid4())
            self.interview_sessionId = st.session_state.interview_sessionId
            print(f"Interview Session: {st.session_state.interview_sessionId}")
        self.data_queue=data_queue
        self.socket_client = socket_client
        self._init_session_states(st.session_state.interview_sessionId, self.userId)
        self._init_display()
        self._create_interviewbot()
        self.interviewer=st.session_state["baseinterview"] if "baseinterview" in st.session_state else None



    
    @st.cache_data()
    def _init_session_states(_self, sessionId, userId):

            st.session_state["mode"]="regular"
            # initialize submitted form variables
            # if "about" not in st.session_state:
            st.session_state["about"]=""
            # if "job_posting" not in st.session_state:
            st.session_state["job_posting"] = ""
            # if "resume_file" not in st.session_state:
            st.session_state["resume_file"] = ""
            # st.session_state["transcribe_client"] = _self.aws_session.client('transcribe')
            st.session_state["tts_client"]= texttospeech.TextToSpeechClient()
            st.session_state["count"]=0
            st.session_state["host"] = "Maya"

            st.session_state["responseInput"] = ''
            if STORAGE == "LOCAL":
                st.session_state["storage"]="LOCAL"
                st.session_state["bucket_name"]=None
                st.session_state["s3_client"]= None
                # st.session_state["window_title"] = pwc.getActiveWindowTitle()
                # if "save_path" not in st.session_state:
                st.session_state["save_path"] = os.environ["INTERVIEW_PATH"]
                # if "temp_path" not in st.session_state:
                st.session_state["temp_path"]  = os.environ["TEMP_PATH"]
                # if "directory_made" not in st.session_state:
            elif STORAGE=="CLOUD":
                st.session_state["lambda_client"] = _self.aws_session.client('lambda')
                st.session_state["storage"]="CLOUD"
                st.session_state["bucket_name"]= os.environ['BUCKET_NAME']
                st.session_state["transcribe_bucket_name"] = os.environ['TRANSCRIBE_BUCKET_NAME']
                st.session_state["polly_bucket_name"] = os.environ['POLLY_BUCKET_NAME']
                st.session_state["s3_client"]= _self.aws_session.client('s3') 
                # if "save_path" not in st.session_state:
                st.session_state["save_path"] = os.environ["S3_INTERVIEW_PATH"]
                # if "temp_path" not in st.session_state:
                st.session_state["temp_path"]  = os.environ["S3_TEMP_PATH"]
            if _self.userId is None:
                paths = [os.path.join(st.session_state.temp_path, st.session_state.interview_sessionId), 
                        os.path.join(st.session_state.save_path, st.session_state.interview_sessionId),
                        os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "downloads"),
                        os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "uploads"),
                        os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "recordings")
                        ]
            else:
                 paths = [os.path.join(_self.userId, st.session_state.temp_path, st.session_state.sessionId),
                    os.path.join(_self.userId, st.session_state.save_path, st.session_state.sessionId),
                    os.path.join(_self.userId, st.session_state.save_path, st.session_state.sessionId, "downloads"),
                    os.path.join(_self.userId, st.session_state.save_path, st.session_state.sessionId, "uploads"),
                 ]
            mk_dirs(paths, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)


                # initialize keyboard listener
            # if "listener" not in st.session_state:
            #     _self.file=None
            #     _self.record=True
            #     new_listener = keyboard.Listener(
            #     on_press=_self.on_press,
            #     on_release=_self.on_release)
            #     st.session_state["listener"] = new_listener
            # initialize backup text session
            # if "text_session" not in st.session_state:
            #     st.session_state["text_session"] = False
 


    def _init_display(_self):

        """ Initializes Streamlit UI. """

        # main_bg_ext = "png"
        
        # st.markdown(
        #  f"""
        #  <style>
        #  .stApp {{
        #      background: url(data:image/{main_bg_ext};base64,{base64.b64encode(open(png_file, "rb").read()).decode()});
        #      background-size: cover
        #  }}
        #  </style>
        #  """,
        #  unsafe_allow_html=True
        # )
        st.markdown(
            """
            <style>
            button[kind="primary"] {
                background: none!important;
                border: none;
                padding: 0!important;
                color: black !important;
                text-decoration: none;
                cursor: pointer;
                border: none !important;
            }
            button[kind="primary"]:hover {
                text-decoration: none;
                color: blue !important;
            }
            button[kind="primary"]:focus {
                outline: none !important;
                box-shadow: none !important;
                color: blue !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # styl = f"""
        # <style>
        #     .stTextInput {{
        #     position: fixed;
        #     bottom: 3rem;
        #     }}
        # </style>
        # """
        # st.markdown(styl, unsafe_allow_html=True)
        with st._main:
            if st.session_state["mode"]=="regular" and "init_interview" in st.session_state:
                 # components.iframe("http://localhost:3001/")
                st.markdown('<a href="http://localhost:3001/" target="_self">click here to proceed</a>', unsafe_allow_html=True)

        with st.sidebar:          
            add_vertical_space(3)
            # st.markdown('''
                        
            # How the mock interview works: 

            # - refresh the page to start a new session   
            # - press R + Space to start recording
            # - press S + Space to stop recording
            # - press Shift + Esc to end the session
                        
            # ''')
            # add_vertical_space(5)
            if "init_interview" not in st.session_state:
                st.markdown("Welcome to your mock interviewer session with an AI interviewer. Please fill out the interview pre-form first so your AI interviewer gets a better understanding of your interview. " )
            if st.session_state["mode"]=="regular" and "init_interview" in st.session_state:
                st.markdown('''
                Troubleshooting:

                1. if the AI cannot hear you, make sure your mic is turned on and enabled
                2. you can switch to the audio only session 

                            ''')
                audio_switch = st.button("switch to audio session", key="switch_audio", type="primary")
                if audio_switch:
                    st.session_state["mode"]="audio"
                    del st.session_state["greeting"]
                    st.session_state["count"] = 0
                    st.rerun()
            if st.session_state["mode"]=="audio":
                st.markdown('''

                Troubleshooting:

                1. if the AI cannot hear you, make sure your mic is turned on and enabled
                2. you can switch to text-only session 

                            ''')
                text_switch = st.button("switch to text only session",  key="switch_text", type="primary")
                if text_switch:
                    st.session_state["mode"]="text"
                    del st.session_state["greeting"]
                    st.session_state["count"] = 0
                    st.rerun()
            if st.session_state["mode"]=="text" or st.session_state["mode"]=="audio":
                st.button("end session",  key="end_session", on_click=_self.interview_feedback)
            # with _self.ai_col:
            #     subtitles = st.button("subtitles",key="turnon_subtitles")
            #     if subtitles:
            #         st.session_state.subtitles=True


            
    def _init_interview_preform(self):

        """ Creates interview form at the beginning of the interview session. """

        st.session_state["modal"] = Modal(title="Welcome to your mock interview session!", key="popup", max_width=1000)
        with st.session_state["modal"].container():
            with st.form( key='interview_form', clear_on_submit=True):
                add_vertical_space(1)
                # st.markdown("Please fill out the form below before we begin")
                st.text_area("tell me about your interview", placeholder="for example, you can say, my interview is with ABC for a store manager position", key="interview_about")
                st.text_input("links (this can be a job posting)", "", key = "interview_links", )
                st.file_uploader(label="Upload your interview material or resume",
                                                type=["pdf","odt", "docx","txt", "zip", "pptx"], 
                                                key = "interview_files",
                                                accept_multiple_files=True)
                add_vertical_space(1)
                st.form_submit_button(label='Submit', on_click=self.form_callback)
            
             
         

    # websocket server
    async def receive_user_input(self, interviewer, loop):

        """ Receives audio transcript and user upload from backend websocket server through a data queue and sends it to AI agent. 
        
        Args:
        
            interviewer: Interview class instance
            
            loop: current event loop
            
        """

        while True:
            user_input = await self.data_queue.get()
            print(f"received transcript from data queue: {user_input}")
            try:
                print("userid:", interviewer.userId)
                # this sends the CPU intensive function to a different blocking thread
                interviewer_response, grader_response = await loop.run_in_executor(None, functools.partial(interviewer.interviewer.askAI, user_input=user_input))
                print("interviewer response:", interviewer_response)
                print("grader response", grader_response)
                data = {"interviewer": interviewer_response, "grader":grader_response}
                json_str = json.dumps(data)
                # this sends the task to the same event loop/
                asyncio.create_task(self.send_response(json_str))
            except Exception as e:
                raise e

    # websocket client
    async def send_response(self, response):

        """ Sends AI response from backend socket client to frontend socket server.
         
          Args:
           
            response: AI generated response """
        
        while self.socket_client.sock.connected:
            # Send a message to the server
            self.socket_client.send(response)
            print(f"Sent message to socket server: {response}")
            await asyncio.sleep(0)
            break
    
       

          
            
    def _create_interviewbot(self, ):

        """ Initializes the main interview session. """


        if "init_interview" not in st.session_state:
            self._init_interview_preform()
            st.session_state["init_interview"]=True
        else:
            if "baseinterview" not in st.session_state:
                print("inside create interviewbot")
                # update interview agents prompts from form variables
                if  st.session_state.about!="" or st.session_state.job_posting!="" or st.session_state.resume_file!="":
                    self.additional_prompt_info, self.generated_dict = self.update_prompt(about=st.session_state.about, job_posting=st.session_state.job_posting, resume_file=st.session_state.resume_file)
                else:
                    self.additional_prompt_info = ""
                    self.generated_dict = {}
                new_interview = InterviewController(st.session_state["interview_sessionId"], self.additional_prompt_info, self.generated_dict)
                st.session_state["baseinterview"] = new_interview
            if "greeting" not in st.session_state:
                st.session_state["greeting"] = st.session_state.baseinterview.generate_greeting(host=st.session_state["host"], mode=st.session_state["mode"])
                # st.session_state["modal"].close()
            # else:
            if st.session_state.mode=="regular":
                if "interview_ui" not in st.session_state:
                    st.session_state["interview_ui"]=True
                    greeting_json = f'{{"name":"{st.session_state.host}", "greeting":"{st.session_state.greeting}"}}'
                    interview = my_component(greeting_json) 
            elif st.session_state.mode=="audio":
                print("entering audio mode")
                if "greeting" in st.session_state and st.session_state.count==0:
                    self.synthesize_ai_response(st.session_state.greeting)
                    st.session_state.count+=1
                user_input=speech_to_text(language='en',use_container_width=True, key="stt", callback=self.audio_callback)
            elif st.session_state.mode=="text":
                print('entering text mode')
                if "greeting" in st.session_state and st.session_state.count==0:
                    self.synthesize_ai_response(st.session_state.greeting)
                    st.session_state.count+=1
                st.text_input("Your response: ",  key="interview_input", on_change = self.chatbox_callback)
                       


                
                # try:
                #     self.new_interview = st.session_state.baseinterview  
                #     # self.listener = st.sesssion_state.listener
                #     # try:
                #     #     self.listener.start()
                #     # # RuntimeError: threads can only be started once  
                #     # except RuntimeError as e:
                #     #     pass
                # except AttributeError as e:
                #     # if for some reason session ended in the middle, may need to do something different from raise exception
                #     raise e 
               
                # with self.human_col:
                #     user_input=speech_to_text(language='en',use_container_width=True,just_once=True,key='STT')
                #     # audio_bytes = audio_recorder(
                #     #     text="Click to record",
                #     #     recording_color="#e8b62c",
                #     #     neutral_color="#6aa36f",
                #     #     icon_name="user",
                #     #     icon_size="6x",
                #     # )
                #     # wav_audio_data = st_audiorec()
                #     # if "text_received" not in st.session_state:
                #     #     st.session_state["text_received"]=""
                #     if user_input:       
                #         # st.session_state["text_received"]=text
                #         st.markdown(user_input)
                #         ai_response = st.session_state.baseinterview.askAI(user_input)
                #         self.synthesize_ai_response(ai_response)
                                # st.audio(resp_bytes)
                        # st.audio(resp_bytes)
                               
                    # audio=mic_recorder(start_prompt="⏺️",stop_prompt="⏹️",key='recorder')
                    # wav_audio_data=None
                    # # if audio:
                    # #     wav_audio_data=audio["bytes"]
                    # if wav_audio_data:
                    # # if audio_bytes:
                    #     # self.write_audio_bytes_to_mp3(audio_bytes, "test.mp3")
                    #     if st.session_state.storage=="LOCAL":
                    #         filename = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                    #         # user_rec_path = os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "recordings", filename, ".mp3")
                    #         # write_file(audio_bytes, user_rec_path)
                    #         user_rec_path = os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "recordings", filename, ".wav")
                    #         write_file(wav_audio_data, user_rec_path)
                    #         user_input=self.transcribe_audio(user_rec_path)
                    #         if user_input:
                    #             ai_response = self.new_interview.askAI(user_input)
                    #             filename = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                    #             ai_rec_path =  os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "recordings", filename, ".mp3")
                    #             resp_bytes=self.synthesize_ai_response(ai_response)
                    #             with self.ai_col:
                    #                 self.autoplay_audio(resp_bytes)
                    #     elif st.session_state.storage=="CLOUD":
                    #         filename = strftime("%Y-%m-%d", gmtime())
                    #         write_path = os.path.join(st.session_state.interview_sessionId, filename+".wav")
                    #         write_file(wav_audio_data, write_path, storage=st.session_state.storage, bucket_name=st.session_state.transcribe_bucket_name, s3=st.session_state.s3_client)
                    #         # write_path = os.path.join(st.session_state.interview_sessionId, filename+".mp3")
                    #         # write_file(audio_bytes, write_path, storage=st.session_state.storage, bucket_name=st.session_state.transcribe_bucket_name, s3=st.session_state.s3_client)
                    #         payload = {"sessionId":st.session_state.interview_sessionId,  "object_url": f"s3://{st.session_state.transcribe_bucket_name}/{write_path}", "prompt_info":self.additional_prompt_info}
                    #         # payload = {"sessionId":st.session_state.sessionId, "prompt_info":self.additional_prompt_info}
                    #         ai_output = self.invoke_lambda(payload)
                    #         if ai_output:
                    #             with self.ai_col:
                    #                 # self.autoplay_audio(ai_output)
                    #                 st.audio(ai_output)
                               
                            #NOTE: this uses AWS Transcribe and Polly with Lambda trigger
                            # ai_response = None
                            # response = st.session_state.lambda_client.invoke(
                            #     FunctionName='transcribe',
                            #     Payload=json.dumps(payload),
                            #     InvocationType= "RequestResponse", 
                            # )
                            # if response:
                            #     data = json.loads(response["Payload"].read().decode("utf-8"))
                            #     print(data)
                            #     if data["statusCode"]==200:
                            #         user_input = data["body"]
                            #         ai_response = self.new_interview.askAI(user_input)
                            # if ai_response is not None:
                            #     payload = {"transcript": ai_response}
                            #     response=st.session_state.lambda_client.invoke(
                            #         FunctionName="tts",
                            #         Payload = payload,
                            #         Invocationtype="RequestResponse",
                            #     )
                            #     if response:
                            #         data = json.loads(response["Payload"].read().decode("utf-8"))
                            #         print(data)
                            #         if data["statusCode"]==200:
                            #             ai_output = data["body"]
                            #             with self.ai_col:
                            #                 self.autoplay_audio(ai_output)
                            #         else:
                            #             print("FAILED TO GET RECORDING")

                      
                # if "listener" not in st.session_state:
                #     ##NOTE: due to listener running on different thread, none of the session states can be accessed thru listener
                #     ## therefore, all needed variables will be saved and accessed thru self
                #     self.file=None
                #     self.record=True
                #     self.interview_sessionId = st.session_state.interview_sessionId
                #     self.window_title = st.session_state.window_title
                #     self.tts_client = st.session_state.tts_client
                #     self.rec_path = os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "recordings")
                #     self.s3=st.session_state.s3_client
                #     self.bucket_name=st.session_state.bucket_name
                #     self.storage=st.session_state.storage
                #     new_listener = keyboard.Listener(
                #     on_press=self.on_press,
                #     # on_press=lambda event: sef.on_press(event, st.session_state.interview_sessionId, st.session_state.window_title),
                #     on_release=self.on_release)
                #     # thread = threading.Thread(target=self._init_listener, args=[self.q])
                #     # add_script_run_ctx(thread, self.ctx)
                #     # thread.start()
                #     # thread.join()
                #     # st.session_state["listener"]=self.q.get()
                #     st.session_state["listener"] = new_listener
                # self.listener = st.session_state.listener
                # try:
                #     self.listener.start()
                # # RuntimeError: threads can only be started once  
                # except RuntimeError as e:
                #     pass


    def invoke_lambda(self, payload, ):

        """Invokes """

        response = st.session_state.lambda_client.invoke(
            FunctionName='tts',
            Payload=json.dumps(payload),
            InvocationType= "RequestResponse", 
        )
        if response:
            data = json.loads(response["Payload"].read().decode("utf-8"))
            print(data)
            if "statusCode" in data:
                if data["statusCode"]==200:
                    output = data["body"]
                    return output
                else:
                    return None


            # try:
            #     self.new_interview = st.session_state.baseinterview  
            #     # self.listener = st.session_state.listener
            #     # try:
            #     #     self.listener.start()
            #     # # RuntimeError: threads can only be started once  
            #     # except RuntimeError as e:
            #     #     pass
            # except AttributeError as e:
            #     # if for some reason session ended in the middle, may need to do something different from raise exception
            #     raise e
                # make directory for session recordings

                # if switch:
                #     st.session_state["text_session"] = True
                # if st.session_state.text_session:
                #     self.text_session()
        
                # self.listener.join()



    def autoplay_audio(self, data: str):

        """Playback for AI response """
        
        # b64 = base64.b64encode(data).decode('utf-8')
        b64=data

        md = f"""
            <audio controls autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(
            md,
            unsafe_allow_html=True,
        )

    

    # def on_press(self, key,):

    #     """ Listens when a keyboards is pressed. """

    #     print("listener key pressed")
    #     if any([key in comb for comb in self.COMBINATION]) and pwc.getActiveWindowTitle()==self.window_title:
    #         self.currently_pressed.add(key)
    #     if self.currently_pressed == self.COMBINATION[0] and pwc.getActiveWindowTitle()==self.window_title:
    #         print("on press: recording")
    #         filename = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    #         #TODO check this path: st.session_state.interview_sessionId not initialized here b/c different thread
    #         self.file =os.path.join(self.rec_path, filename+".wav")
    #         thread = threading.Thread(target = self.record_audio2)
    #         add_script_run_ctx(thread, self.ctx)
    #         thread.start()
    #         # self.record_audio2()
    #     if self.currently_pressed == self.COMBINATION[1] and pwc.getActiveWindowTitle()==self.window_title:
    #         self.listener.stop()
    #         print("on press: quitting")
    #         thread = threading.Thread(target=self.interview_feedback)
    #         add_script_run_ctx(thread, self.ctx)
    #         thread.start()
    #     if self.currently_pressed == self.COMBINATION[2] and pwc.getActiveWindowTitle()==self.window_title:
    #         self.record = False
    #         print("on press: stopping")
    #         try:
    #             with open(self.file) as f:
    #                 f.flush()
    #                 f.close()
    #         except RuntimeError as e:
    #             raise e
    #         print("Recorded Human and written to file.")
    #         user_input = self.transcribe_audio2()
    #         response = self.new_interview.askAI(user_input)
    #         # print(response)
    #         # with self.ai_col: 
    #         #     self.typewriter(response, speed=2)           
    #         self.play_response2(response)
    #         self.record = True

         
    # def on_release(self, key):

    #     """ Listens when a keyboard is released. """
        
    #     try:
    #         self.currently_pressed.remove(key)
    #     except KeyError:
    #         pass
            

    # def record_audio2(self):

    #     """ Records audio and write it to file. """

    #     def callback(indata, frame_count, time_info, status):
    #         self.q.put(indata.copy())
    #     with sf.SoundFile(self.file, mode='x', samplerate=fs,
    #             channels=channels) as file:
    #         with sd.InputStream(samplerate=fs, device=device,
    #                     channels=channels, callback=callback):
    #             while self.record:
    #                 file.write(self.q.get())
        
                
     # inspired by: https://github.com/VRSEN/langchain-agents-tutorial
    # def transcribe_audio(self, file) -> str or None:

    #     """ Sends audio file to OpenAI's Whisper model for trasncription and response """
    #     try:
    #         with open(file, "rb") as audio_file:
    #         # with open(temp_audio.name, "rb") as audio_file:
    #             transcript = openai.Audio.transcribe("whisper-1", audio_file)
    #         print(f"Successfully transcribed file from openai whisper: {transcript}")
    #         # os.remove(temp_audio.name)
    #         question = transcript["text"].strip()
    #         return question
    #     except Exception as e:
    #         st.info("oops, someething happened, please record again.")
    #         return None

    
    def synthesize_ai_response(self, ai_response: str,) -> Any:

        """ Generates Text-to-Speech using Polly by invoking AWS Lambda. If fails, resorts to calling Google Cloud Speech API. """
        try:
            payload={"text":ai_response}
            data = self.invoke_lambda(payload)
            resp_bytes = data["audio"]
        except Exception:
            resp_bytes=self.tts(ai_response)
        if resp_bytes:
            with self.ai_col:
                print("before calling autoplay")
                self.autoplay_audio(resp_bytes)
                # if st.session_state.subtitles:
                self.typewriter(ai_response, speed=3)




    def tts(self, response:str) -> Any:

        """ Generates Text-to-Speech using Google Cloud Speech API. """

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=response)
        # Build the voice request, select the language code ("en-US") and the ssml
        # voice gender ("neutral")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        # Perform the text-to-speech request on the text input with the selected
        # voice parameters and audio file type
        response = st.session_state.tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        # The response's audio_content is binary.
        return response.audio_content
    


    # inspired by: https://github.com/VRSEN/langchain-agents-tutorial
    # def transcribe_audio2(self) -> str:

    #     """ Sends audio file to OpenAI's Whisper model for trasncription and response """
    #     try:
    #         with open(self.file, "rb") as audio_file:
    #         # with open(temp_audio.name, "rb") as audio_file:
    #             transcript = openai.Audio.transcribe("whisper-1", audio_file)
    #             print(f"Successfully transcribed file from openai whisper: {transcript}")
    #         # os.remove(temp_audio.name)
    #     except Exception as e:
    #         raise e
    #     question = transcript["text"].strip()
    #     # with self.human_col:
    #     #     self.typewriter(question)
    #     return question
    
    # def play_response2(self, response: str) -> None:

    #     # tts = ElevenLabsText2SpeechTool()
    #     # tts= GoogleCloudTextToSpeechTool()
    #     # speech_file = tts.run(response)
    #     # tts.play(speech_file)
    #     # st.session_state.tts.play(response)
    #     # Set the text input to be synthesized
    #     #NOTE: can be switched to AWS boto3 POLLY, outputs mp3 file
    #     synthesis_input = texttospeech.SynthesisInput(text=response)
    #     # Build the voice request, select the language code ("en-US") and the ssml
    #     # voice gender ("neutral")
    #     voice = texttospeech.VoiceSelectionParams(
    #         language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    #     )
    #     # Select the type of audio file you want returned
    #     audio_config = texttospeech.AudioConfig(
    #         audio_encoding=texttospeech.AudioEncoding.MP3
    #     )
    #     # Perform the text-to-speech request on the text input with the selected
    #     # voice parameters and audio file type
    #     response = self.tts_client.synthesize_speech(
    #         input=synthesis_input, voice=voice, audio_config=audio_config
    #     )
    #     # The response's audio_content is binary.
    #     filename=strftime("%Y-%m-%d %H:%M:%S", gmtime())
    #     #NOTE: try S3 with CloudFront to stream out the audio
    #     end_path=os.path.join(self.rec_path,  filename, ".mp3")
    #     with open(end_path, "wb") as out:
    #         # Write the response to the output file.
    #         out.write(response.audio_content)
    #         print(f'Audio content written to file {end_path}')
    #     playsound.playsound(end_path, True)

    
    # def play_generated_audio(self, text, voice="Bella", model="eleven_monolingual_v1"):

    #     """ Deploys Eleven Labs for AI generated voice playback """

    #     audio = generate(text=text, voice=voice, model=model)
    #     play(audio)

    def interview_feedback(self):

        """ Provides interview session feedback as a downloadable file to the user. """

        with placeholder.container():
            modal = Modal(key="feedback_popup", title="Thank you for your participation in the interview session. I have a printout of your session summary and I value your feedback too!")
            with modal.container():
                feedback = self.new_interview.retrieve_feedback()
                questions = self.new_interview.craft_questions()
                followup=self.new_interview.write_followup()
                feedback_path = self.output_printout(feedback+questions+followup)
                with open(feedback_path) as f:
                    st.download_button('Download my session summary', f)  # Defaults to 'text/plain'
                with st.form(key="feedback_form", clear_on_submit=True):
                    submit = st.form_submit_button()
                    #TODO write feedback to AI



    def form_callback(self):

        """ Processes form information during form submission callback. """

        try:
            files = st.session_state.interview_files 
            if files:
                self.process_uploads(files, "files")
        except Exception:
            pass
        try:
            links = st.session_state.interview_links
            if links:
                self.process_uploads(links, "links")
        except Exception:
            pass 
        try:
            about = st.session_state.interview_about
            if about:
                self.process_uploads(about, "about")     
        except Exception:
            pass
    
    def audio_callback(self):

        """Creates audio only interview session. """

        user_input = st.session_state.stt_output
        if user_input:
            with self.human_col:
                st.markdown(user_input)
                ai_response = st.session_state.baseinterview.askAI(user_input)
                self.synthesize_ai_response(ai_response)
 



    def _init_text_session(self):

        """ Creates text only interview session. """

        # stop the keyboard listener
        # try:
        #     st.session_state.listener.stop()
        # except Exception:
        #     pass


        styl = f"""
        <style>
            .stTextInput {{
            position: fixed;
            bottom: 3rem;
            }}
        </style>
        """
        st.markdown(styl, unsafe_allow_html=True)

        st.session_state.count+=1
        # if "interview_dict" not in st.session_state:
        #     st.session_state["interview_dict"] = {"ai":[], "human":[]}
        # # if 'interview_responses' not in st.session_state:
        # #     st.session_state['interview_responses'] = list()
        # # if 'interview_questions' not in st.session_state:
        #     greeting = "Welcome to your mock interview! Are you ready to get started?"
        #     # st.session_state['interview_questions'] = [greeting]
        #     st.session_state["interview_dict"]["ai"].append(greeting)
        # with self.ai_col:
        #     self.typewriter(r"$\textsf{\Large Welcome to your mock interview! Are you ready to get started? $")
    
            
            
        # # col1,  col2= st.columns(2, gap="large")
        # if 'interview_response' not in st.session_state:
        #     st.session_state['interview_response'] = ""
        # if 'interview_question' not in st.session_state:
                

                
        # with col1:
        #     if "question_container" not in st.session_state:
        #         st.session_state["question_container"] = st.container()
        # with col2:
        #     if "response_container" not in st.session_state:
        #         st.session_state["response_container"] = st.container()
        # response_container = st.container()

        if 'responseInput' not in st.session_state:
            st.session_state.responseInput = ''
        # def submit():
        #     st.session_state.responseInput = st.session_state.interview_input
        #     st.session_state.interview_input = ''    
        # # User input
        # ## Function for taking user provided prompt as input
        # def get_text():
        #     st.text_input("Your response: ", "", key="interview_input", on_change = submit)
        #     return st.session_state.responseInput
        # ## Applying the user input box
        # with response_container:
        #     user_input = get_text()
        #     response_container = st.empty()
        #     st.session_state.responseInput='' 


        # if user_input:

        #     # res = question_container.container()
        #     # streamlit_handler = StreamlitCallbackHandler(
        #     #     parent_container=res,
        #     #     # max_thought_containers=int(max_thought_containers),
        #     #     # expand_new_thoughts=expand_new_thoughts,
        #     #     # collapse_completed_thoughts=collapse_completed_thoughts,
        #     # )
        #     user_answer = user_input
        #     # answer = chat_agent.run(mrkl_input, callbacks=[streamlit_handler])
        #     ai_question = self.new_interview.askAI(user_answer, callbacks = None)
        #     st.session_state.interview_questions.append(ai_question)
        #     st.session_state.interview_responses.append(user_answer)
        # if st.session_state['interview_responses']:
        #     for i in range(len(st.session_state['interview_responses'])):
        #         with col1:
        #             message(st.session_state['interview_questions'][i], key=str(i), avatar_style="initials", seed="AI_Interviewer", allow_html=True)
        #         with col2:
        #             message(st.session_state['interview_responses'][i], is_user=True, key=str(i) + '_user',  avatar_style="initials", seed="Yueqi", allow_html=True)
        # try:
        #     with self.ai_col:
        #         # message(st.session_state.interview_questions[-1])
        #         # st.markdown(st.session_state.interview_questions[-1])
        #         st.markdown(st.session_state["interview_dict"]["ai"][-1])
        #     with self.human_col:
        #         # message(st.session_state.interview_responses[-1])
        #         # st.markdown(st.session_state.interview_responses[-1])
        #         st.markdown(st.session_state["interview_dict"]["human"][-1])
        # except Exception:
        #     pass
        
        st.text_input("Your response: ",  key="interview_input", on_change = self.chatbox_callback)
        # st.chat_input(key="interview_input", on_submit = self.chatbox_callback)



    def chatbox_callback(self):

        """ Processes user input from chatbox and prefilled question selection after submission. """
        
        st.session_state.responseInput = st.session_state.interview_input
        st.session_state.interview_input = ''    
        with self.human_col:
            st.markdown(st.session_state.responseInput)
        ai_response = st.session_state.baseinterview.askAI(st.session_state.responseInput, 
                                           callbacks = None)
        # self.synthesize_ai_response(ai_response,)
        with self.ai_col:
            self.typewriter(ai_response, speed=3)

        # st.session_state.interview_responses.append(st.session_state.interview_input)
        # st.session_state.interview_questions.append(response)
        # if response:
        #     with self.ai_col:
        #         self.typewriter(response, speed=3)
        # st.session_state.interview_responses.append(st.session_state.interview_input)
        # st.session_state.interview_questions.append(response)
        # st.session_state["interview_dict"]["human"].append(st.session_state.interview_input)
        # st.session_state["interview_dict"]["ai"].append(response)


    def typewriter(self, text: str, speed=1): 

        """ Displays AI response playback at a particular speed. """

        tokens = text.split()
        container = st.empty()
        for index in range(len(tokens) + 1):
            curr_full_text = " ".join(tokens[:index])
            container.markdown(curr_full_text)
            time.sleep(1 / speed)

    

    def update_prompt(self, about: str, job_posting: str, resume_file:str) -> str:

        """ Updates prompts of interview agent and grader before initialization. 

        Args:

            about (str): preprocessed user's about interview input

            job_posting (str): job posting file path

            resume_file (str): resume file path  

        Retunrs:

            a concatenated string o f additional information such as company description, job specification found in the inputs. 
        
        """


        additional_interview_info = about
        try:
            resume_content = read_txt(resume_file)
        except Exception:
            resume_content = ""
        event_loop = asyncio.get_event_loop()
        generated_dict=get_generated_responses(about_me=about, posting_path=job_posting, resume_content = resume_content)
        job = generated_dict.get("job", "")
        job_description=generated_dict.get("job description", "")
        company_description = generated_dict.get("company description", "")
        job_specification=generated_dict.get("job specification", "")
        # resume_field_names = generated_dict.get("field names", "")
        # if job!=-1:
        #     # get top n job interview questions for this job
        #     query = f"top 10 interview questions for {job}"
        #     response = get_web_resources(query)
        #     additional_interview_info += f"top 10 interview questions for {job}: {response}"
        # if resume_field_names!="":
        #     for field_name in resume_field_names:
        #         additional_interview_info += f"""applicant's {field_name}: {generated_dict.get(field_name, "")}"""
        # if job_description!="":
        #     additional_interview_info += f"job description: {job_description} \n"
        # if job_specification!="":
        #     additional_interview_info += f"job specification: {job_specification} \n"
        # if company_description!="":
        #     additional_interview_info += f"company description: {company_description} \n"

        return additional_interview_info, generated_dict
    

    def process_uploads(self, uploads: Any, upload_type:str) -> None:

        """ Processes user information. 
        
        Args:
        
            uploads: user upload
            
            upload_type: files, links or about
            
        """

        end_paths = []
        if upload_type=="files":
            for uploaded_file in uploads:
                file_ext = Path(uploaded_file.name).suffix
                filename = str(uuid.uuid4())+file_ext
                tmp_save_path = os.path.join(st.session_state.temp_path, st.session_state.interview_sessionId, filename)
                write_file(uploaded_file.getvalue(), tmp_save_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                if convert_to_txt(tmp_save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                    end_paths.append(end_path)
        if upload_type=="links":
            end_path = os.path.join(st.session_state.save_path, st.session_state.interview_sessionId, "uploads", str(uuid.uuid4())+".txt")
            links = re.findall(r'(https?://\S+)', uploads)
            if html_to_text(links, save_path=end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                end_paths.append(end_path)
        if upload_type=="about":
            st.session_state["about"] = uploads
        for end_path in end_paths:
            content_safe, content_type, content_topics = check_content(end_path)
            print(content_type, content_safe, content_topics) 
            if content_safe:
                    # EVERY CONTENT TYPE WILL BE USED AS INTERVIEW MATERIAL
                record_name = self.userId if self.userId is not None else st.session_state.sessionId
                vs_path = user_vs_name if st.session_state.storage=="CLOUD" else os.path.join(st.session_state.save_path, st.session_state.sessionId, user_vs_name)
                update_vectorstore(end_path=end_path, vs_path =vs_path,  index_name=user_vs_name, record_name=record_name, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                if content_type=="resume":
                    print(f"user uploaded a resume file")
                    st.session_state["resume_file"]=end_path
                if content_type=="job posting":
                    print(f"user uploaded job posting")
                    st.session_state["job_posting"]= end_path
                st.toast(f"your {content_type} is successfully submitted")
            else:
                delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                st.toast(f"Failed processing your material. Please try again!")




    

    
    # def update_vectorstore(self, content_type:str, end_path:str) -> None: 

    #     """ Converts uploaded content to vector store.
         
    #       Args:

    #         content_type: one of the following ["resume", "cover letter", "user profile", "job posting", "personal statement", "other"]

    #         end_path: file_path   
            
    #     """

    #     if content_type!="other":
    #         vs_name = content_type.strip().replace(" ", "_")
    #         vs = create_vectorstore("faiss", end_path, "file", vs_name)
    #     else:
    #         vs_name = "interview_material"
    #         vs = merge_faiss_vectorstore(vs_name, end_path)
    #     vs_path =  os.path.join(save_path, st.session_state.userid, vs_name)
    #     vs.save_local(vs_path)




  
# async def inputstream_generator(channels=1, **kwargs):
#     """Generator that yields blocks of input data as NumPy arrays."""
#     q_in = asyncio.Queue()
#     loop = asyncio.get_event_loop()

#     def callback(indata, frame_count, time_info, status):
#         loop.call_soon_threadsafe(q_in.put_nowait, (indata.copy(), status))

#     stream = sd.InputStream(callback=callback, channels=channels, **kwargs)
#     with stream:
#         while True:
#             indata, status = await q_in.get()
#             yield indata, status

# async def stream_generator(blocksize, *, channels=1, dtype='float32',
#                            pre_fill_blocks=10, **kwargs):
#     """Generator that yields blocks of input/output data as NumPy arrays.

#     The output blocks are uninitialized and have to be filled with
#     appropriate audio signals.

#     """
#     assert blocksize != 0
#     q_in = asyncio.Queue()
#     q_out = queue.Queue()
#     loop = asyncio.get_event_loop()

#     def callback(indata, outdata, frame_count, time_info, status):
#         loop.call_soon_threadsafe(q_in.put_nowait, (indata.copy(), status))
#         outdata[:] = q_out.get_nowait()

#     # pre-fill output queue
#     for _ in range(pre_fill_blocks):
#         q_out.put(np.zeros((blocksize, channels), dtype=dtype))

#     stream = sd.Stream(blocksize=blocksize, callback=callback, dtype=dtype,
#                        channels=channels, **kwargs)
#     with stream:
#         while True:
#             indata, status = await q_in.get()
#             outdata = np.empty((blocksize, channels), dtype=dtype)
#             yield indata, outdata, status
#             q_out.put_nowait(outdata)


# async def print_input_infos(**kwargs):
#     """Show minimum and maximum value of each incoming audio block."""
#     async for indata, status in inputstream_generator(**kwargs):
#         if status:
#             print(status)
#         print('min:', indata.min(), '\t', 'max:', indata.max())


# async def wire_coro(**kwargs):
#     """Create a connection between audio inputs and outputs.

#     Asynchronously iterates over a stream generator and for each block
#     simply copies the input data into the output block.

#     """
#     async for indata, outdata, status in stream_generator(**kwargs):
#         if status:
#             print(status)
#         outdata[:] = indata

# async def main(**kwargs):
#     print('Some informations about the input signal:')
#     try:
#         await asyncio.wait_for(print_input_infos(), timeout=2)
#     except asyncio.TimeoutError:
#         pass
#     print('\nEnough of that, activating wire ...\n')
#     audio_task = asyncio.create_task(wire_coro(**kwargs))
#     for i in range(10, 0, -1):
#         print(i)
#         await asyncio.sleep(1)
#     audio_task.cancel()
#     try:
#         await audio_task
#     except asyncio.CancelledError:
#         print('\nwire was cancelled')
# async def run():
#         # empty list of tasks (from previous streamlit session) 
# # and make sure that every is cancelled
#     print("IM BEING RAN")
#     while st.session_state['tasks']:
#         t = st.session_state['tasks'].pop()
#         t.cancel()
#         del t # not sure whether this is needed

#     tasks = []
#     # now reschedule coroutines
#     for cor in coroutines:
#         tasks.append(asyncio.ensure_future(cor))

#     # store in st.session_state to access them after a rerun 
#     st.session_state['tasks'] = tasks
    
#     # let them run
#     _ = await asyncio.gather(*tasks, return_exceptions=False)
#         # Thread(target=lambda: asyncio_run(self._create_interviewbot(), daemon=True).start())
#     # asyncio.run_coroutine_threadsafe(self._create_interviewbot(), event_loop)

# if __name__ == '__main__':

#     event_loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(event_loop)
#     nest_asyncio.apply()
#     web_socket_server = Socket()
#     interviewer = Interview(data_queue=web_socket_server.data_queue)
#     # data = YourDataProcessor(data_queue=web_socket_server.data_queue)

#     tasks = [
#         asyncio.ensure_future(web_socket_server._initialize_socket()),
#         asyncio.ensure_future(interviewer.receive_transcript()),
#         # asyncio.ensure_future( data.process_data())
#     ]

#     event_loop.run_until_complete(asyncio.gather(*tasks))


# if __name__=="__main__":
#     # Interview()
#     event_loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(event_loop)
#     nest_asyncio.apply()
#     interviewer = Interview()
class SocketClient():

    def __init__(self):

        if "socket_client" not in st.session_state:
            # self.socket_client=None
            self._init_socket_client()
        else:
            self.socket_client = st.session_state.socket_client

    def _init_socket_client(self):
        # if "socket_client" not in st.session_state:
        def on_message(ws, message):
            print(message)

        def on_error(ws, error):
            print("error:", error)

        def on_close(ws, close_status_code, close_msg):
            print("### closed ### ")
            if close_status_code or close_msg:
                print("close status code: " + str(close_status_code))
                print("close message: " + str(close_msg))

        def on_open(ws):
            print("Opened connection")

        def run_websocket():
            self.socket_client.run_forever()

        # if self.socket_client is None:
        st.session_state["socket_client"] = websocket.WebSocketApp(uri,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
        self.socket_client = st.session_state.socket_client
        threading.Thread(target=run_websocket, daemon=True).start()


try:
    event_loop = asyncio.get_event_loop()
except Exception:
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
nest_asyncio.apply()
web_socket_server = SocketServer()
web_socket_client = SocketClient()
# print(st.session_state.socket_client)
# print(web_socket_client.socket_client)
interviewer = Interview(data_queue=web_socket_server.data_queue, socket_client=web_socket_client.socket_client)
# partial_create_interviewbot = functools.partial(interviewer._create_interviewbot, interviewer.interview_sessionId)
# event_loop.run_in_executor(None, partial_create_interviewbot)
if interviewer.interviewer is not None:
    tasks = [
        asyncio.ensure_future(web_socket_server._init_socket_server()),
        asyncio.ensure_future(interviewer.receive_user_input(interviewer, event_loop,)),
    ]

    event_loop.run_until_complete(asyncio.gather(*tasks))
    event_loop.run_forever()
