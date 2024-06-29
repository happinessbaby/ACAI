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
from utils.basic_utils import delete_file, mk_dirs, move_file
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  check_content, process_links, process_uploads, process_inputs, retrieve_or_create_job_posting_info, retrieve_or_create_resume_info
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
# from time import gmtime, strftime
# import playsound
# from streamlit_modal import Modal
import json
from langchain.tools import ElevenLabsText2SpeechTool, GoogleCloudTextToSpeechTool
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import re
from utils.cookie_manager import CookieManager
from utils.aws_manager import get_client
import pywinctl as pwc
from interview_component import my_component
from google.cloud import texttospeech
# from pydub import AudioSegment
# import wave
# from audio_recorder_streamlit import audio_recorder
# from streamlit_mic_recorder import mic_recorder,speech_to_text
# from speech_recognition import Recognizer, AudioData
import asyncio
import json
import base64
import threading
# from six.moves import queues
from google.cloud import speech
from utils.socket_server import SocketServer, Transcoder
from utils.async_utils import asyncio_run
import nest_asyncio
import websocket
from utils.whisper_stt import whisper_stt
from utils.streamlit_utils import nav_to


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

# interview_options=["phone", "panel"]

class Interview():


    # COMBINATION = [{keyboard.KeyCode.from_char('r'), keyboard.Key.space}, {keyboard.Key.shift, keyboard.Key.esc}, {keyboard.Key.enter}]
    ctx = get_script_run_ctx()
    # currently_pressed = set()


    def __init__(self, data_queue, socket_client):

        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
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
                if _self.userId is not None:
                    st.session_state["interview_save_path"] = os.path.join(os.environ["USER_PATH"], _self.userId, "interview")
                else:
                    st.session_state["interview_save_path"] =os.environ["INTERVIEW_PATH"]
            elif STORAGE=="CLOUD":
                st.session_state["lambda_client"] = get_client("lambda")
                st.session_state["s3_client"]= get_client("s3")
                st.session_state["storage"]= STORAGE
                st.session_state["bucket_name"]= os.environ['BUCKET_NAME']
                st.session_state["transcribe_bucket_name"] = os.environ['TRANSCRIBE_BUCKET_NAME']
                st.session_state["polly_bucket_name"] = os.environ['POLLY_BUCKET_NAME']
                # if "save_path" not in st.session_state:
                if _self.userId is not None:
                    st.session_state["interview_save_path"] =os.path.join(os.environ["S3_USER_PATH"], _self.userId, "interview")
                else:
                    st.session_state["interview_save_path"] = os.environ["S3_INTERVIEW_PATH"]
            #TODO: logged in users have access to interview progression analysis
            paths = [st.session_state["interview_save_path"],
                    os.path.join(st.session_state.interview_save_path, st.session_state.interview_sessionId),
                    # os.path.join(st.session_state.interview_save_path, "downloads", st.session_state.interview_sessionId),
                    os.path.join(st.session_state.interview_save_path, st.session_state.interview_sessionId, "uploads"),
                    os.path.join(st.session_state.interview_save_path,  st.session_state.interview_sessionId, "recordings")
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
 
    @st.experimental_dialog("Tell me about your interview!", width="large")
    def interview_form_popup(self):
        """"""

        st.session_state["init_interview"]=False
        def add_links(count):
            # c1, c2=st.columns([5, 1])
            # with c1:
            if count==0:
                st.text_input(label =f"Link",
                                key = f"interview_links_{count}", 
                            help ="This can be an interview material from online sources",
                                on_change=self.form_callback,
                                )
            else:
                st.text_input(label="hidden", 
                               key = f"interview_links_{count}", 
                              label_visibility="hidden")
            # with c2:
            placeholder = st.empty()
            another = placeholder.checkbox(label="add another",
                        key=f"checkbox_link_{count}",
            )
            if another:
                placeholder.empty()
                add_links(count++1)
        with st.expander("About you (optional)"):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.text_area("Introduce yourself",
                             placeholder="for example, you can say, I'm an aspiring project manager who has 5 years of management experience",
                             on_change=self.form_callback,
                             key="interview_about_me"
                             )
        # with c2:
            #NOTE: this is to help retrieve industry specific vector store for interview material
            # industry_options =  ["Healthcare", "Computer & Technology", "Advertising & Marketing", "Aerospace", "Agriculture", "Education", "Energy", "Entertainment", "Fashion", "Finance & Economic", "Food & Beverage", "Hospitality", "Manufacturing", "Media & News", "Mining", "Pharmaceutical", "Telecommunication", " Transportation" ]
            # st.selectbox("Industry",
            #             index=None, 
            #             key="interview_industry",
            #                 options=industry_options,
            #                 on_change=self.form_callback,
            #                 )
            with c2:
                st.file_uploader(label="Resume", 
                                 accept_multiple_files=False, 
                                 on_change=self.form_callback,
                                   key="interview_resume")
        with st.expander("About the interview (optional)"):
            c1, x, c2 = st.columns([5, 1, 5])
            with c1:
                st.text_area("Interview content", 
                            placeholder="for example, you can say, my interview is with ABC for a store manager position",
                            key="interview_about_job",
                            on_change=self.form_callback,
                )
            with x:
                add_vertical_space(3)
                st.markdown("or")
            with c2:
                job_posting = st.radio(f" ", 
                                key="job_posting_radio", options=["job description", "job posting link"], 
                                index = 1 if "job_description"  not in st.session_state else 0
                                )
                if job_posting=="job posting link":
                    job_posting_link = st.text_input(label="Job posting link",
                                                    key="interview_job_posting", 
                                                    on_change=self.form_callback,
                                                        )
                elif job_posting=="job description":
                    job_description = st.text_area("Job description", 
                                                key="interview_job_descriptionx", 
                                                value=st.session_state.job_description if "interview_job_description" in st.session_state else "",
                                                    on_change=self.form_callback, 
                                                    )
        with st.expander("Add your interview materials"):
            c1, c2=st.columns([1, 1])
            with c1:
                add_links(0)
            with c2:
                st.file_uploader(label="Files",
                                type=["pdf","odt", "docx","txt", "zip", "pptx"], 
                                key = "interview_files",
                                accept_multiple_files=True, 
                                on_change= self.form_callback,
                                )
        if st.button("Submit",key="preform_submit_button"):
            st.session_state["init_interview"]=True
            st.rerun()
        if st.button("skip", type="primary"):
            st.session_state["init_interview"]=False
            st.rerun()


    
    def _init_display(_self):

        """ Initializes Streamlit UI. """

        def get_base64_of_bin_file(bin_file):
            with open(bin_file, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode()

        def set_png_as_page_bg(png_file):
            bin_str = get_base64_of_bin_file(png_file)
            page_bg_img = '''
            <style>
            .stApp {
            background-image: url("data:image/png;base64,%s");
            background-size: cover;
            }
            </style>
            ''' % bin_str
            
            st.markdown(page_bg_img, unsafe_allow_html=True)
            return
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
            if "mode" not in st.session_state:
                print("waiting for user to pick a mode")
                # set_png_as_page_bg("./background/enter_interview.png")
                with st.container():
                    c1, _, c2=st.columns([1, 1, 1])
                    with c1:
                        if st.button("Enter panel room", key="panel_mode_button",):
                            st.session_state["mode"]="panel interview"
                            st.rerun()           
                    with c2:
                        if st.button("Enter phone interview", key="phone_mode_button",):
                            st.session_state["mode"]="phone interview"
                            st.rerun()
            if "mode" in st.session_state and "init_interview" not in st.session_state:
                _self.interview_form_popup()
            if "mode" in st.session_state and st.session_state["mode"]=="panel interview" and "baseinterview" in st.session_state:
                print("initializing panel interview ui")
                 # components.iframe("http://localhost:3001/")
                # st.markdown('<a href="http://localhost:3001/" target="_self">click here to proceed</a>', unsafe_allow_html=True)
                greeting_json = f'{{"name":"{st.session_state.host}", "greeting":"{st.session_state.greeting}"}}'
                interview = my_component(greeting_json) 
                nav_to("http://localhost:3001/" )
            elif   "mode" in st.session_state and st.session_state["mode"]=="phone interview" and "baseinterview" in st.session_state:
                print('entering phone mode')
                with st.container():
                    # user_input =speech_to_text(start_prompt="🔴", stop_prompt="⏺️", language='en', key="voice_input", callback=_self.chat_callback, args=("voice", ))
                    with st.session_state.human_col:
                        text = whisper_stt(start_prompt="🔴", stop_prompt="⏺️", language='en', key="voice_input", callback=_self.chat_callback, args=("voice", ))  
                    if text:
                        print(text)
                    if "greeting" in st.session_state and "interviewer_response" not in st.session_state :
                        _self.synthesize_ai_response(st.session_state.greeting)
                    if "interview_input" in st.session_state and "interviewer_response" in st.session_state:
                        with st.session_state.human_col:
                            st.session_state.placeholder_human.markdown(st.session_state.interview_input)
                        with st.session_state.ai_col:
                            # if "input_type" in st.session_state and st.session_state["input_type"]=="voice":
                            _self.synthesize_ai_response(st.session_state.interviewer_response)
                            # elif  "input_type" in st.session_state and st.session_state["input_type"]=="text":
                            #     _self.typewriter(st.session_state.interviewer_response, speed=3)
                    if "grader_response" in st.session_state:
                        with st.session_state.feedback_col:
                            with st.session_state.placeholder_expander.expander("How am I doing?"):
                                placeholder_feedback=st.empty()
                                placeholder_feedback.write(st.session_state.grader_response)
                    # st.session_state.placeholder_chat.chat_input("Your response: ",  key=f"chat_input", on_submit = _self.chat_callback, args=("text", ))




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
    


          
            
    def _create_interviewbot(self, ):

        """ Initializes the main interview session. """


        if "init_interview" not in st.session_state:
            print("waiting user to fill out interview preform")
        else:
            if "baseinterview" not in st.session_state:
                print("inside create interviewbot")
                # update interview agents prompts from form variables
                if st.session_state["init_interview"]:
                    generated_dict = self.update_prompt()
                new_interview = InterviewController(self.userId,  st.session_state["interview_sessionId"],generated_dict)
                st.session_state["baseinterview"] = new_interview
            if "greeting" not in st.session_state:
                st.session_state["greeting"] = st.session_state.baseinterview.generate_greeting(host=st.session_state["host"])
            if "post_interview_questions" not in st.session_state:
                st.session_state["post_interview_questions"] = st.session_state.baseinterview.generate_questions()
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
    


    def form_callback(self,):

        """ Processes form information during form submission callback. """

        try:
            files = st.session_state.interview_files 
            if files:
                self.process(files, "files")
        except Exception:
            pass
        try:
            links = st.session_state.interview_links
            if links:
                self.process(links, "links")
        except Exception:
            pass 
        try:
            job_posting=st.session_state.interview_job_posting
            if job_posting:
                # st.session_state.job_posting=""
                self.process(job_posting, "job_posting")
        except Exception:
            pass
        try:
            job_description=st.session_state.interview_job_descriptionx
            if job_description:
               self.process(job_description, "job_description")
        except Exception:
            pass
        try:
            resume=st.session_state.interview_resume
            if resume:
                self.process([resume],"resume" )
        except Exception:
            pass

     
        

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

        generated_dict = {}
        generated_dict.update({"about_interview": st.session_state.interview_about_job if "interview_about_job" in st.session_state else ""})
        generated_dict.update({"about_me": st.session_state.interview_about_me if "interview_about_me" in st.session_state else ""})
        # interview_industry = st.session_state.interview_industry if "interview_industry" in st.session_state else ""
        user_upload_dict=st.session_state["user_upload_dict"] if "user_upload_dict" in st.session_state else ""
        if user_upload_dict:
            learning_material = user_upload_dict.get("learning material", "")
            generated_dict.update({"learning_material":learning_material})
            job_posting = user_upload_dict.get("job posting", "")
            job_description = user_upload_dict.get("job description", "")
            resume = user_upload_dict.get("resume", "")
            if job_posting or job_description:
                job_dict = retrieve_or_create_job_posting_info(posting_path=job_posting, 
                                                    job_description=job_description)
                generated_dict.update({"job_info_dict":job_dict})
            if resume:
                resume_dict = retrieve_or_create_resume_info(resume, )
                generated_dict.update({"resume_info_dict":resume_dict})
        return generated_dict
    

    def process(self, uploads: Any, upload_type:str) -> None:

        """ Processes user information. 
        
        Args:
        
            uploads: user upload
            
            upload_type: files, links or about
            
        """
        #TODO: better html and pdf reader that can process graphs and charts (see deeplearning jupyter notoebook)
        if upload_type=="files":
            result = process_uploads(uploads, st.session_state.interview_save_path, st.session_state.interview_sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type!="browser error"and content_type!="empty":
                    if content_type=="learning material":
                        self.save_material_paths(end_path)
                    st.toast(f"your {content_type} is successfully sent to AI ")
                else:
                    delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                    st.toast(f"Failed processing your material. Please try again!") 

        elif upload_type=="links":
            result = process_links(uploads, st.session_state.interview_save_path, st.session_state.interview_sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type!="browser error"and content_type!="empty":
                    if content_type=="learning material":
                        self.save_material_paths(end_path)
                        st.toast(f"your {content_type} is successfully sent to AI ")
                else:
                    delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                    st.toast(f"Failed processing your material. Please try again!") 
        elif upload_type=="job_posting":
            result = process_links(uploads, st.session_state.interview_save_path, st.session_state.interview_sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="job posting":
                    st.session_state["user_upload_dict"].update({content_type:end_path})
                else:
                    st.info("Please upload your job posting link here")
            else:
                st.info("That didn't work. Please try pasting the content in job description instead.")
        elif upload_type=="job_description":
            result = process_inputs(uploads, match_topic="job posting or job description")
            if result is not None:
                st.session_state["interview_job_description"] = uploads  
                st.session_state["user_upload_dict"].update({content_type:uploads})
            else:
                st.info("Please share a job description here")
        elif upload_type=="resume":
            result = process_uploads(uploads, st.session_state.interview_save_path, st.session_state.interview_sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="resume":
                    st.session_state["user_upload_dict"].update({content_type:uploads})
                else:
                    st.info("Please upload your resume here")
            else:
                st.info("Please upload your resume here")


       

    def save_material_paths(end_path, ):
            
        destination_path=os.path.join(st.session_state.interview_save_path, "uploads", st.session_state.interview_sessionId, "learning_material", str(uuid.uuid4()), ".txt")
        destination_dir = os.path.dirname(destination_path)
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        # Move the file
        move_file(end_path, destination_path)
        st.session_state["user_upload_dict"].update({"learning material":destination_dir})



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
