import streamlit as st
from streamlit_chat import message
from streamlit_extras.add_vertical_space import add_vertical_space
from pathlib import Path
import random
import time
import openai
import os
import uuid
from backend.mock_interviewer import InterviewController
# from callbacks.capturing_callback_handler import playback_callbacks
from utils.basic_utils import convert_to_txt, read_txt, retrieve_web_content, html_to_text, delete_file, mk_dirs, write_file, read_file, move_file
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  check_content
import asyncio
import functools
from typing import Any, Dict, Union
# from pynput.keyboard import Key, Controller
# from pynput import keyboard
# import sounddevice as sd
# from sounddevice import CallbackFlags
# import soundfile as sf
# import numpy  as np# Make sure NumPy is loaded before it is used in the callback
# assert np  # avoid "imported but unused" message (W0611)
# import tempfile
import openai
# from elevenlabs import generate, play, set_api_key
from time import gmtime, strftime
import playsound
from streamlit_modal import Modal
import json
from langchain.tools import ElevenLabsText2SpeechTool, GoogleCloudTextToSpeechTool
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import re
from utils.cookie_manager import get_cookie, get_all_cookies, decode_jwt
from utils.aws_manager import get_aws_session,  get_client
import pywinctl as pwc
from interview_component import my_component
from google.cloud import texttospeech
from pydub import AudioSegment
import wave
from audio_recorder_streamlit import audio_recorder
from streamlit_mic_recorder import mic_recorder,speech_to_text
from speech_recognition import Recognizer, AudioData
import asyncio
import json
import base64
import threading
# from six.moves import queue
from google.cloud import speech
from utils.socket_server import SocketServer, Transcoder
from utils.async_utils import asyncio_run
import nest_asyncio
import websocket
from utils.whisper_stt import whisper_stt


_ = load_dotenv(find_dotenv()) # read local .env file



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

st.markdown("<style> ul {display: none;} </style>", unsafe_allow_html=True)


class Interview():


    # COMBINATION = [{keyboard.KeyCode.from_char('r'), keyboard.Key.space}, {keyboard.Key.shift, keyboard.Key.esc}, {keyboard.Key.enter}]
    ctx = get_script_run_ctx()
    # currently_pressed = set()
    # q = queue.Queue()

    

    def __init__(self, data_queue, socket_client):
        self.cookie = get_cookie("userInfo")
        if self.cookie:
            self.userId = decode_jwt(self.cookie, "test").get('username')
            print("Cookie:", self.userId)
        else:
            self.userId = None
        if "interview_sessionId" not in st.session_state:
            st.session_state["interview_sessionId"] = str(uuid.uuid4())
            self.interview_sessionId = st.session_state.interview_sessionId
            print(f"Interview Session: {st.session_state.interview_sessionId}")
        self.data_queue=data_queue
        self.socket_client = socket_client
        self._init_session_states()
        self._create_interviewbot()
        self._init_display()
        self.interviewer=st.session_state["baseinterview"] if "baseinterview" in st.session_state else None



    
    @st.cache_data()
    def _init_session_states(_self,):

            st.session_state["mode"]=None
            st.session_state["user_upload_dict"] = {}
            # initialize submitted form variables
            # if "about" not in st.session_state:
            st.session_state["about"]=""
            st.session_state["industry"]=""
            # st.session_state["transcribe_client"] = _self.aws_session.client('transcribe')
            st.session_state["tts_client"]= texttospeech.TextToSpeechClient()
            st.session_state["host"] = "Maya"
            # st.session_state["responseInput"] = ''
            # st.session_state["input_counter"]=0
            _, st.session_state["voice_col"], st.session_state["feedback_col"] = st.columns([3, 2, 1])
            with st.session_state.voice_col:
                st.session_state["placeholder_voice"]=st.empty()
            with st.session_state.feedback_col:
                st.session_state["placeholder_expander"]=st.empty()
                # st.session_state["feedback_expander"]= st.expander("How am I doing?")
                # with st.session_state.feedback_expander:
                #     st.session_state["placeholder_grader"]=st.empty()
            st.session_state["ai_col"], st.session_state["human_col"] = st.columns(2, gap="large")
            with st.session_state.ai_col:
                st.session_state["placeholder_ai"] = st.empty()
            with st.session_state.human_col:
                st.session_state["placeholder_human"]=st.empty()
            # st.session_state["chat_input"] = st.chat_input("Your response: ",  key="interview_input", on_submit = _self.chatbox_callback)
            # st.session_state["message_history"] = init_table(_self.aws_session, st.session_state.interview_sessionId)
            st.session_state["placeholder_chat"]=st.empty()
            if STORAGE == "LOCAL":
                st.session_state["storage"]=STORAGE
                st.session_state["bucket_name"]=None
                st.session_state["s3_client"]= None
                # st.session_state["window_title"] = pwc.getActiveWindowTitle()
                # if "save_path" not in st.session_state:
                st.session_state["save_path"] =os.environ["INTERVIEW_PATH"]
                # if "temp_path" not in st.session_state:
                # st.session_state["temp_path"]  = os.environ["TEMP_PATH"]
                # if "directory_made" not in st.session_state:
            elif STORAGE=="CLOUD":
                st.session_state["lambda_client"] = get_client("lambda")
                st.session_state["s3_client"]= get_client("s3")
                st.session_state["storage"]= STORAGE
                st.session_state["bucket_name"]= os.environ['BUCKET_NAME']
                st.session_state["transcribe_bucket_name"] = os.environ['TRANSCRIBE_BUCKET_NAME']
                st.session_state["polly_bucket_name"] = os.environ['POLLY_BUCKET_NAME']
                # if "save_path" not in st.session_state:
                st.session_state["save_path"] = os.environ["S3_INTERVIEW_PATH"]
                # if "temp_path" not in st.session_state:
                # st.session_state["temp_path"]  = os.environ["S3_TEMP_PATH"]
            if _self.userId is None:
                paths = [
                        # os.path.join(st.session_state.temp_path, st.session_state.interview_sessionId), 
                        # os.path.join(st.session_state.save_path, st.session_state.interview_sessionId),
                        os.path.join(st.session_state.save_path, "downloads", st.session_state.interview_sessionId),
                        os.path.join(st.session_state.save_path, "uploads", st.session_state.interview_sessionId),
                        os.path.join(st.session_state.save_path, "recordings", st.session_state.interview_sessionId)
                        ]
            else:
                 paths = [
                    #  os.path.join(_self.userId, st.session_state.temp_path, st.session_state.sessionId),
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
            if "init_interview" not in st.session_state:
                with st.container():
                    c1, c2=st.columns([8, 1])
                    #TODO: display interview tips UI with some html component
                    with c2:
                        placeholder_skip = st.empty()
                        skip = placeholder_skip.button("Skip the interview form", type="primary")
                        if skip:
                            st.session_state["init_interview"]=False
                            placeholder_skip.empty()
                            # st.rerun()
                    # _self.interview_loading()
                    # interview_loading(container)
            if "init_interview" in st.session_state and st.session_state["mode"]==None:
                with st.container():
                    c1, _, c2=st.columns([1, 1, 1])
                    with c1:
                        placeholder_interview=st.empty()
                        interview_mode=placeholder_interview.button("Enter interview room", key="interview_mode_button",)
                    with c2:
                        placeholder_practice=st.empty()
                        practice_mode = placeholder_practice.button("Enter practice mode", key="practice_mode_button",)
                    if interview_mode:
                        st.session_state.mode="regular"
                        placeholder_interview.empty()
                        placeholder_practice.empty()
                    if practice_mode:
                        st.session_state.mode="text_and_voice"
                        placeholder_interview.empty()
                        placeholder_practice.empty()
            if st.session_state["mode"]=="regular" and "init_interview" in st.session_state and "baseinterview" in st.session_state:
                print("initializing interview ui")
                 # components.iframe("http://localhost:3001/")
                # st.markdown('<a href="http://localhost:3001/" target="_self">click here to proceed</a>', unsafe_allow_html=True)
                greeting_json = f'{{"name":"{st.session_state.host}", "greeting":"{st.session_state.greeting}"}}'
                interview = my_component(greeting_json) 
                _self.nav_to("http://localhost:3001/" )
            elif  st.session_state.mode=="text_and_voice" and "init_interview" in st.session_state and "baseinterview" in st.session_state:
                print('entering text mode')
                with st.container():
                    # user_input =speech_to_text(start_prompt="🔴", stop_prompt="⏺️", language='en', key="voice_input", callback=_self.chat_callback, args=("voice", ))
                    text = whisper_stt(start_prompt="🔴", stop_prompt="⏺️", language='en', key="voice_input", callback=_self.chat_callback, args=("voice", ))  
                    if text:
                        print(text)
                    if "interview_input" in st.session_state and "interviewer_response" in st.session_state:
                        with st.session_state.human_col:
                            st.session_state.placeholder_human.markdown(st.session_state.interview_input)
                        with st.session_state.ai_col:
                            if "input_type" in st.session_state and st.session_state["input_type"]=="voice":
                                _self.synthesize_ai_response(st.session_state.interviewer_response)
                            elif  "input_type" in st.session_state and st.session_state["input_type"]=="text":
                                _self.typewriter(st.session_state.interviewer_response, speed=3)
                    if "grader_response" in st.session_state:
                        with st.session_state.feedback_col:
                            with st.session_state.placeholder_expander.expander("How am I doing?"):
                                placeholder_feedback=st.empty()
                                placeholder_feedback.write(st.session_state.grader_response)
                    st.session_state.placeholder_chat.chat_input("Your response: ",  key=f"chat_input", on_submit = _self.chat_callback, args=("text", ))

                       


        with st.sidebar:          
            add_vertical_space(10)
            # st.markdown('''s
                        
            # How the mock interview works: 

            # - refresh the page to start a new session   
            # - press R + Space to start recording
            # - press S + Space to stop recording
            # - press Shift + Esc to end the session
                        
            # ''')
            # add_vertical_space(5)
            if "init_interview" not in st.session_state:
                placeholder_form=st.empty()
                with placeholder_form.form("Interview Form", clear_on_submit=True):
                # st.markdown("Interview Form")
                    st.text_area("Tell me about your interview", placeholder="for example, you can say, my interview is with ABC for a store manager position", key="interview_about",)
                    industry_options =  ["Healthcare", "Computer & Technology", "Advertising & Marketing", "Aerospace", "Agriculture", "Education", "Energy", "Entertainment", "Fashion", "Finance & Economic", "Food & Beverage", "Hospitality", "Manufacturing", "Media & News", "Mining", "Pharmaceutical", "Telecommunication", " Transportation" ]
                    st.selectbox("Industry", index=None, key="interview_industry", options=industry_options,)
                    st.text_input("Links", placeholder="please separate each link with a comma", key = "interview_links", help="This can be a job posting or your interview material from online sources" )
                    st.file_uploader(label="Interview materials",
                                    type=["pdf","odt", "docx","txt", "zip", "pptx"], 
                                    key = "interview_files",
                                    accept_multiple_files=True, 
                                    help="This can also be your resume",
                                    )
                    add_vertical_space(1)      
                    clicked=st.form_submit_button("Submit", on_click=_self.form_callback, args=(placeholder_form, placeholder_skip))


            
    # def _init_interview_preform(self):

    #     """ Creates interview form at the beginning of the interview session. """

    #     st.session_state["modal"] = Modal(title="Welcome to your mock interview session!", key="popup", max_width=1000)
    #     with st.session_state["modal"].container():
    #         # with st.form( key='interview_form', clear_on_submit=True):
    #         add_vertical_space(1)
    #         st.markdown("Please fill out the form below before we begin")
    #         st.text_area("tell me about your interview", placeholder="for example, you can say, my interview is with ABC for a store manager position", key="interview_about", on_change=self.form_callback)
    #         st.text_input("links (this can be a job posting)", "", key = "interview_links", on_change=self.form_callback )
    #         st.file_uploader(label="Upload your interview material or resume",
    #                                         type=["pdf","odt", "docx","txt", "zip", "pptx"], 
    #                                         key = "interview_files",
    #                                         accept_multiple_files=True, 
    #                                         on_change=self.form_callback,
    #                                         )
    #         add_vertical_space(1)
    #         st.button("Submit", key="preform_submit_button", on_click=self.submit_callback)
                # st.form_submit_button(label='Submit', on_click=self.form_callback)
            
    # def submit_callback(self):
    #     st.session_state["init_interview"]=True    


        
 


    # websocket server
    async def receive_user_input(self, interviewer, loop):

        """ Receives audio transcript and user upload from backend websocket server through a data queue and sends it to AI agent. 
        
        Args:
        
            interviewer: Interview class instance
            
            loop: current event loop
            
        """

        while True:
            user_input = await self.data_queue.get()
            print(f"received input from data queue: {user_input}")
            if user_input=="END":
                feedback = interviewer.interviewer.retrieve_feedback()
                data = {"interviewer":"", "grader":feedback}
            else:
                # this sends the CPU intensive function to a different blocking thread
                interviewer_response = await loop.run_in_executor(None, functools.partial(interviewer.interviewer.askInterviewer, user_input=user_input))
                grader_response =  await loop.run_in_executor(None, functools.partial(interviewer.interviewer.askGrader, user_input=user_input))
                print("interviewer response:", interviewer_response)
                print("grader response:", grader_response)
                data = {"interviewer": interviewer_response, "grader":grader_response}
            try: 
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
    
       
    # def show_interview_tips(self, container):
    #     while True:
    #         #Temporary 
    #         container.write("Please fill out the form on the sidebar. The more you provide the more personalized your session will be. ")
    #         time.sleep(5)
    #         container.write("If AI cannot hear you, please check if your mic is turned on and check the sound volume. ")
    #         time.sleep(5)
    #         container.write("Do not refresh the page or your interview session will restart")
    #         time.sleep(5)


          
            
    def _create_interviewbot(self, ):

        """ Initializes the main interview session. """


        if "init_interview" not in st.session_state:
            # self._init_interview_preform()
            # if st.session_state["modal"].is_open()==False:
            #     st.session_state["init_interview"]=False
            print("waiting user to fill out pre-form")
            # st.session_state["init_interview"]=True
        else:
            if "baseinterview" not in st.session_state:
                print("inside create interviewbot")
                # update interview agents prompts from form variables
                # if  st.session_state.about!="" or st.session_state.job_posting!="" or st.session_state.resume_file!="":
                if st.session_state["init_interview"]:
                    self.about_interview, self.interview_industry, self.learning_material, self.generated_dict = self.update_prompt()
                else:
                    self.about_interview = ""
                    self.interview_industry=""
                    self.generated_dict = {}
                    self.learning_material= ""
                print("about_interview:", self.about_interview)
                print("generated_dict", self.generated_dict)
                print("learning material", self.learning_material)
                print("interview industry",self.interview_industry)
                new_interview = InterviewController(self.userId,  st.session_state["interview_sessionId"],self.about_interview, self.interview_industry, self.generated_dict, self.learning_material)
                st.session_state["baseinterview"] = new_interview
            if "greeting" not in st.session_state:
                st.session_state["greeting"] = st.session_state.baseinterview.generate_greeting(host=st.session_state["host"])
                # st.session_state["greeting_json"] = f'{{"name":"{st.session_state.host}", "greeting":"{st.session_state.greeting}"}}'
                # st.session_state["modal"].close()

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
    def nav_to(self, url):
        nav_script = """
            <meta http-equiv="refresh" content="0; url='%s'">
        """ % (url)
        st.write(nav_script, unsafe_allow_html=True)

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
        
        b64 = base64.b64encode(data).decode('utf-8')
        # st.audio(data)
        audio_placeholder=st.empty()
        # b64=data
        md = f"""
            <audio controls autoplay hidden>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        audio_placeholder.markdown(
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
            print("Invoked Lambda Polly")
        except Exception:
            resp_bytes=self.tts(ai_response)
            print("Invoked Google TTS")
        if resp_bytes:
            with st.session_state.ai_col:
                self.autoplay_audio(resp_bytes)
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
    


    def form_callback(self, form_placeholder, skip_placeholder):

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
        try:
            industry = st.session_state.interview_industry
            if industry:
                self.process_uploads(industry, "industry")     
        except Exception:
            pass
        st.session_state["init_interview"]=True
        skip_placeholder.empty()
        form_placeholder.empty()
        

    # def voice_callback(self):

    #     # "access this transcription directly in the session state by adding an '_output' suffix to the key you chose for the widget"
    #     if st.session_state.voice_input_output:
    #         user_input = st.session_state.voice_input_output
    #         with st.session_state.human_col:
    #             st.session_state.placeholder_human.markdown(user_input)
    #         ai_response = st.session_state.baseinterview.askInterviewer(user_input)
    #         st.session_state["grader_response"] = st.session_state.baseinterview.askGrader(user_input)
    #         self.synthesize_ai_response(ai_response)


    def chat_callback(self, type):

        """ Processes user input from chatbox and prefilled question selection after submission. """
        
        if type=="text":
            interview_input = st.session_state.chat_input
        elif type=="voice":
            interview_input = st.session_state.voice_input_output
        st.session_state["grader_response"]= st.session_state.baseinterview.askGrader(interview_input)
        st.session_state["interviewer_response"] = st.session_state.baseinterview.askInterviewer(interview_input, 
                                           callbacks = None)
        st.session_state["interview_input"] = interview_input
        st.session_state["input_type"] = type

    
    def retrieve_feedback(self):
        
        """Retrieves live feedback from interview grader"""
        with st.container():
            st.write(st.session_state.grader_response)

        

    def typewriter(self, text: str, speed=1): 

        """ Displays AI response playback at a particular speed. """

        tokens = text.split()
        for index in range(len(tokens) + 1):
            curr_full_text = " ".join(tokens[:index])
            st.session_state.placeholder_ai.markdown(curr_full_text)
            time.sleep(1 / speed)

    

    def update_prompt(self, ) -> Union[str, str, Dict[str, str]]:

        """ Updates prompts of interview agent and grader before initialization.


        Returns:

            about interview description, path to interview material, and a dictionary of additional user information generated through AI
        
        """
    
        about_interview = st.session_state["about"]
        interview_industry = st.session_state["industry"]
        learning_material = st.session_state["user_upload_dict"].get("learning material", "")
        # event_loop = asyncio.get_event_loop()
        #TODO run the following in separated thread
        generated_dict=get_generated_responses(about_me=st.session_state.about, 
                                               posting_path=st.session_state["user_upload_dict"].get("resume", ""),
                                                 resume_path = st.session_state["user_upload_dict"].get("job posting", ""),
                                                 program_path = st.session_state["user_upload_dict"].get("education program", "")
                                                 )
        # job = generated_dict.get("job", "")
        # job_description=generated_dict.get("job description", "")
        # company_description = generated_dict.get("company description", "")
        # job_specification=generated_dict.get("job specification", "")
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

        return about_interview, interview_industry, learning_material, generated_dict
    

    def process_uploads(self, uploads: Any, upload_type:str) -> None:

        """ Processes user information. 
        
        Args:
        
            uploads: user upload
            
            upload_type: files, links or about
            
        """
        #TODO: better html and pdf reader that can process graphs and charts (see deeplearning jupyter notoebook)

        end_paths = []
        filename = str(uuid.uuid4())
        if upload_type=="files":
            for uploaded_file in uploads:
                file_ext = Path(uploaded_file.name).suffix
                # filename = str(uuid.uuid4())+file_ext
                tmp_save_path = os.path.join(st.session_state.save_path, "uploads", st.session_state.interview_sessionId, filename+file_ext)
                end_path = os.path.join(st.session_state.save_path, "uploads", st.session_state.interview_sessionId, filename+".txt")
                if write_file(uploaded_file.getvalue(), tmp_save_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                    if convert_to_txt(tmp_save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                        end_paths.append(end_path)
                        print("Successfully uploaded user file")
                else:
                    print("failed to upload user file")
        elif upload_type=="links":
            # filename =  str(uuid.uuid4())+".txt"
            end_path = os.path.join(st.session_state.save_path, "uploads", st.session_state.interview_sessionId, filename+".txt")
            links = re.findall(r'(https?://\S+)', uploads)
            if html_to_text(links, save_path=end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                end_paths.append(end_path)
                print("Successfully uploaded user link")
            else:
                print("failed to upload user link")
        elif upload_type=="about":
            st.session_state["about"] = uploads
            st.toast("Your interview description is successfully sent to AI")
        elif upload_type=="industry":
            st.session_state["industry"]=uploads
        for end_path in end_paths:
            content_safe, content_type, content_topics = check_content(end_path)
            print(content_type, content_safe, content_topics) 
            if content_safe:
                if content_type!="browser error" and content_type!="empty":
                    ##TODO: save to different directory according to content type
                    if content_type=="learning material":
                        destination_path=os.path.join(st.session_state.save_path, "uploads", st.session_state.interview_sessionId, "learning_material", filename+".txt")
                        destination_dir = os.path.dirname(destination_path)
                        if not os.path.exists(destination_dir):
                            os.makedirs(destination_dir)
                        # Move the file
                        move_file(end_path, destination_path)
                        st.session_state["user_upload_dict"].update({content_type:destination_dir})
                    else:
                        st.session_state["user_upload_dict"].update({content_type:end_path})
                    # EVERY CONTENT TYPE WILL BE USED AS INTERVIEW MATERIAL
                # record_name = self.userId if self.userId is not None else st.session_state.sessionId
                # vs_path = user_vs_name if st.session_state.storage=="CLOUD" else os.path.join(st.session_state.save_path, st.session_state.sessionId, user_vs_name)
                # update_vectorstore(end_path=end_path, vs_path =vs_path,  index_name=user_vs_name, record_name=record_name, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                    st.toast(f"your {content_type} is successfully sent to AI ")
            else:
                delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                st.toast(f"Failed processing your material. Please try again!")
       




    # def save_session(self, ):

    #     #conversation history is automatically saved to dynamodb ideally



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
if interviewer.interviewer is not None:
    tasks = [
        asyncio.ensure_future(web_socket_server._init_socket_server()),
        asyncio.ensure_future(interviewer.receive_user_input(interviewer, event_loop,)),
    ]

    event_loop.run_until_complete(asyncio.gather(*tasks))
    event_loop.run_forever()
