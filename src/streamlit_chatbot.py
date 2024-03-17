import streamlit as st
from streamlit_chat import message
from streamlit_extras.add_vertical_space import add_vertical_space
import extra_streamlit_components as stx
from pathlib import Path
import random
import time
import openai
import os
import uuid
from io import StringIO
from langchain_community.callbacks import StreamlitCallbackHandler
from backend.career_advisor import ChatController
from callbacks.capturing_callback_handler import playback_callbacks
from utils.basic_utils import convert_to_txt, read_txt, retrieve_web_content, html_to_text, delete_file, mk_dirs, write_file, read_file
from utils.openai_api import get_completion, num_tokens_from_text, check_content_safety
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  check_content, evaluate_content, generate_tip_of_the_day, shorten_content, generate_user_info
import re
from json import JSONDecodeError
from multiprocessing import Process, Queue, Value
import pickle
import requests
from functools import lru_cache
from typing import Any, List, Union
import multiprocessing as mp
from utils.langchain_utils import (merge_faiss_vectorstore, create_input_tagger, create_vectorstore, update_vectorstore,
retrieve_vectorstore, create_record_manager, update_index, split_doc_file_size, create_compression_retriever)
import openai
import json
from st_pages import show_pages_from_config, add_page_title, show_pages, Page, Section
from st_clickable_images import clickable_images
from st_click_detector import click_detector
from streamlit_extras.switch_page_button import switch_page
from streamlit_modal import Modal
import base64
from langchain.tools import tool
import streamlit.components.v1 as components, html
from PIL import Image
from my_component import my_component
# from thread_safe_st import ThreadSafeSt
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.callbacks.base import BaseCallbackHandler
import threading
import queue
import boto3
from boto3.dynamodb.conditions import Key, Attr
import yaml
import decimal
import time
from cookie_manager import get_cookie, get_all_cookies
from utils.dynamodb_utils import create_table, retrieve_sessions, save_current_conversation, check_attribute_exists, save_user_info, init_table
from aws_manager import get_aws_session, request_aws4auth
from st_multimodal_chatinput import multimodal_chatinput
from streamlit_datalist import stDatalist
import time
import re
from langchain.schema import ChatMessage





_ = load_dotenv(find_dotenv()) # read local .env file

# Either this or add_indentation() MUST be called on each page in your
# app to add indendation in the sidebar

# Optional -- adds the title and icon to the current page
# add_page_title()

# Specify what pages should be shown in the sidebar, and what their titles and icons
# should be


show_pages(
    [
        Page("streamlit_user.py", f"User"),
        Section(name="Settings"),
        Page("streamlit_chatbot.py", "Career Help", "🏠"),
        Page("streamlit_interviewbot.py", "Mock Interview", ":books:"),
        # Page("streamlit_resources.py", "My Journey", ":busts_in_silhouette:" ),
    ]
)

STORAGE = os.environ['STORAGE']
bucket_name = os.environ['BUCKET_NAME']
user_vs_name = os.environ["USER_CHAT_VS_NAME"]
openai.api_key = os.environ['OPENAI_API_KEY']
max_token_count = os.environ['MAX_TOKEN_COUNT']
message_key = {
"PK": os.environ["PK"],
"SK": os.environ["SK"],
}
topic = "jobs"
# st.write(get_all_cookies())


class Chat():

    ctx = get_script_run_ctx()
    cookie = get_cookie("userInfo")
    aws_session = get_aws_session()
    # chatinput = multimodal_chatinput()

    
    def __init__(self):

        # NOTE: userId is retrieved from browser cookie
        if self.cookie:
            # self.userId = self.cookie.split("###")[1]
            self.userId = re.split("###|@", self.cookie)[1]
            print(self.userId)
        else:
            self.userId = None
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states(self.userId, st.session_state.sessionId)
        self._init_display()
        self._create_chatbot()

        

    # NOTE: Cache differently depending on if user is logged in and re-caches for each new session
    @st.cache_data()
    def _init_session_states(_self, userId, sessionId):

        """ Initializes Streamlit session states. """

        # if "tip" not in st.session_state:
            # tip = generate_tip_of_the_day(topic)
            # st.session_state["tip"] = tip
            # st.write(tip)
        # if "sessionId" not in st.session_state:
        #     st.session_state["sessionId"] = str(uuid.uuid4())
        # #     print(f"Session: {st.session_state.sessionId}")
        # if "messages" not in st.session_state:
        st.session_state["messages"] = [ChatMessage(role="assistant", content="How can I help you?")]
        #TODO, get dynamodb message history to work
        # message_history = DynamoDBChatMessageHistory(table_name=_self.userId, session_id=st.session_state.sessionId, key=message_key, boto3_session=_self.aws_session)
        st.session_state["message_history"]=None
        # new_chat = ChatController(st.session_state.sessionId, chat_memory=message_history)
        # st.session_state["basechat"] = new_chat
        ## hacky way to clear uploaded files once submitted
        # if "file_counter" not in st.session_state:
        st.session_state["file_counter"] = 0
        # if "input_counter" not in st.session_state:
        st.session_state["input_counter"] = 0
        # if "template_path" not in st.session_state:
        st.session_state["template_path"] = os.environ["TEMPLATE_PATH"]
        ## NOTE: for logged in users, paths will be different
        if _self.userId is not None:
            # if "dnm_table" not in st.session_state:
            st.session_state["dnm_table"] = init_table(session=_self.aws_session, userId=_self.userId)
           

            # if "past_human_sessions" not in st.session_state:
            #     # retrieve past conversation if user logged in
            #     human, ai = retrieve_sessions(st.session_state.dnm_table, _self.userId)
            #     print(human, ai)
            #     st.session_state["past_human_sessions"] = human
            #     st.session_state["past_ai_sessions"] = ai
            # if st.session_state.past_human_sessions:
            #     st.session_state.messages.extendleft(ChatMessage(role="assistant", content=ai))
            #     st.session_state.messages.extendleft(ChatMessage(role="user", content=human))

        # if "message_history" not in st.session_state:
        #     st.session_state["message_history"] = StreamlitChatMessageHistory(key="langchain_messages")
        ## questions stores User's questions
        # if 'questions' not in st.session_state:
        #     st.session_state['questions'] = list()
        # ## responses stores AI generated responses
        # if 'responses' not in st.session_state:
        #     st.session_state['responses'] = list()
        # # hack to clear text after user input
        # if 'questionInput' not in st.session_state:
        #     st.session_state["questionInput"] = None  
        if STORAGE == "LOCAL":
            st.session_state["storage"]="LOCAL"
            st.session_state["bucket_name"]=None
            st.session_state["s3_client"]= None
            # if "save_path" not in st.session_state:
            st.session_state["save_path"] = os.environ["CHAT_PATH"]
            # if "temp_path" not in st.session_state:
            st.session_state["temp_path"]  = os.environ["TEMP_PATH"]
        elif STORAGE=="CLOUD":
            st.session_state["storage"]="CLOUD"
            st.session_state["bucket_name"]=bucket_name
            st.session_state["s3_client"]= _self.aws_session.client('s3') 
            st.session_state["awsauth"] = request_aws4auth(_self.aws_session)
            # if "save_path" not in st.session_state:
            st.session_state["save_path"] = os.environ["S3_CHAT_PATH"]
            # if "temp_path" not in st.session_state:
            st.session_state["temp_path"]  = os.environ["S3_TEMP_PATH"]
        if _self.userId is None:
            paths = [os.path.join(st.session_state.temp_path, st.session_state.sessionId), 
                    os.path.join(st.session_state.save_path, st.session_state.sessionId),
                    os.path.join(st.session_state.save_path, st.session_state.sessionId, "downloads"),
                    os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads"),
                    ]
        else:
            paths = [os.path.join(_self.userId, st.session_state.temp_path, st.session_state.sessionId),
                    os.path.join(_self.userId, st.session_state.save_path, st.session_state.sessionId),
                    os.path.join(_self.userId, st.session_state.save_path, st.session_state.sessionId, "downloads"),
                    os.path.join(_self.userId, st.session_state.save_path, st.session_state.sessionId, "uploads"),
                     ]
        mk_dirs(paths, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)

    # @st.cache_data()
    def _init_display(_self):

        """ Initializes UI. """

         # textinput_styl = f"""
        # <style>
        #     .stTextInput {{
        #     position: fixed;
        #     bottom: 3rem;
        #     }}
        # </style>
        # """
        # selectbox_styl = f"""
        # <style>
        #     .stSelectbox {{
        #     position: fixed;
        #     bottom: 4.5rem;
        #     right: 0;
        #     }}
        # </style>
        # """

        # if 'spinner_placeholder' not in st.session_state:
        #     st.session_state["spinner_placeholder"] = st.empty()

        # sample_questions = [
        #     "help me generate a cover letter", 
        #     "Evaluate my resume",
        #     "rewrite my resume using a new template",
        #     "tailor my document to a job position",
        # ]
        # selected_questions = st.multiselect(
        #     label="Job Titles",
        #     options=sample_questions,
        #     default=None,
        #     placeholder="Choose an option",
        # )
        # chat_input = st.chat_input(placeholder="Chat with me:",
        #                             key="input",)
        # selected_questions.append(chat_input)
        # st.markdown(textinput_styl, unsafe_allow_html=True)
        # st.markdown(selectbox_styl, unsafe_allow_html=True)

        with st.sidebar:
            add_vertical_space(1)
            st.markdown('''
                                                
            Chat with me, Upload & Share, or click on the Mock Interview tab above to try it out! 
                                                
            ''')

            # st.button("Upload my files", key="upload_file_button", on_click=self.file_upload_popup)
            # st.button("Share a link", key="link_button", on_click=self.link_share_popup)
            with st.expander("Upload & Share"):
                st.file_uploader(label="Files",
                                accept_multiple_files=True,
                                help = "This can be a resume, cover letter, job posting, study material, etc.",
                                key= f"files_{str(st.session_state.file_counter)}",
                                on_change=_self.form_callback)
                link = st.checkbox("job link")
                description = st.checkbox("job description")
                if link:
                    st.text_area(label="Links", 
                            placeholder="This can be a job posting site for example", 
                            key = "links", 
                            # label_visibility="hidden",
                            help="If the link failed, please try to save the content into a file and upload it.",
                        on_change=_self.form_callback)
                if description:
                    st.text_area(label="About",
                                key="aboutJob",
                                placeholder="What should I know about this job?",
                                on_change=_self.form_callback)
                # additional = st.radio(label="Additional information?", 
                #          options=["link", "job description"], 
                #          key="select_options",
                #          index=None,)
                # if additional=="link":
                #     st.text_area(label="Links", 
                #             placeholder="This can be a job posting site for example", 
                #             key = "links", 
                #             # label_visibility="hidden",
                #             help="If the link failed, please try to save the content into a file and upload it.",
                #         on_change=_self.form_callback)
                # elif additional=="job description":
                #     st.text_area(label="About",
                #                 key="aboutJob",
                #                 placeholder="What should I know about this job?",
                #                 on_change=_self.form_callback)
                  
            with st.expander("Download your files"):
                if "download_placeholder" not in st.session_state:
                    st.session_state["download_placeholder"]=st.empty()
      

            # with st.expander("Past sessions"):
            #     if "past_placeholder" not in st.session_state:
            #         st.session_state["past_placeholder"]=st.empty()

            # test = st.button("save session")
            # if test:
            #    self.save_current_session()
                

            # st.markdown('''
                                                
            # Note: 
               
            # Only the most recent uploaded files, links, and about me will be used.
                        
            # If you refresh the page, your session conversation and downloads will be lost.
                                                
            # ''')
        




                
  
    def _create_chatbot(self,):

        """ Creates the main chat interface. """

        # with placeholder.container():

        if "basechat" not in st.session_state:
            new_chat = ChatController(st.session_state.sessionId, chat_memory=st.session_state.message_history)
            st.session_state["basechat"] = new_chat

        try:
            self.new_chat = st.session_state.basechat
            # self.msgs = st.session_state.message_history
        except AttributeError as e:
            raise e
        # streamHandler = StreamHandler([st.empty()])
    
        # Initialize chat history
        # msgs = StreamlitChatMessageHistory(key="langchain_messages")
        # view_messages = st.expander("View the message contents in session state")
        # SAMPLE_QUESTIONS = {
        #     "":"",
        #     # "upload my files": "upload",
        #     "help me generate a cover letter": "generate",
        #     "Evaluate my resume": "evaluate",
        #     "rewrite my resume using a new template": "reformat",
        #     "tailor my document to a job position": "tailor",
        # }


        # Sidebar section
        # with st.sidebar:
        #     add_vertical_space(1)
        #     st.markdown('''
                                                
        #     Chat with me, Upload & Share, or click on the Mock Interview tab above to try it out! 
                                                
        #     ''')

        #     # st.button("Upload my files", key="upload_file_button", on_click=self.file_upload_popup)
        #     # st.button("Share a link", key="link_button", on_click=self.link_share_popup)
        #     with st.expander("Upload & Share"):
        #         st.file_uploader(label="Files",
        #                         accept_multiple_files=True,
        #                         help = "This can be a resume, cover letter, job posting, study material, etc.",
        #                         key= f"files_{str(st.session_state.file_counter)}",
        #                         on_change=self.form_callback)
        #         additional = st.radio(label="Additional information?", 
        #                  options=["link", "job description"], 
        #                  key="select_options",
        #                  index=None,)
        #         if additional=="link":
        #             st.text_area(label="Links", 
        #                     placeholder="This can be a job posting site for example", 
        #                     key = "links", 
        #                     # label_visibility="hidden",
        #                     help="If the link failed, please try to save the content into a file and upload it.",
        #                 on_change=self.form_callback)
        #         elif additional=="job description":
        #             st.text_area(label="About",
        #                         key="aboutJob",
        #                         placeholder="What should I know about this job?",
        #                         on_change=self.form_callback)
                  
        #     with st.expander("Download your files"):
        #         if "download_placeholder" not in st.session_state:
        #             st.session_state["download_placeholder"]=st.empty()
      

        #     # with st.expander("Past sessions"):
        #     #     if "past_placeholder" not in st.session_state:
        #     #         st.session_state["past_placeholder"]=st.empty()

        #     # test = st.button("save session")
        #     # if test:
        #     #    self.save_current_session()
                

        #     st.markdown('''
                                                
        #     Note: 
               
        #     Only the most recent uploaded files, links, and about me will be used.
                        
        #     If you refresh the page, your session conversation and downloads will be lost.
                                                
        #     ''')
        

        
            # st.text_area(label="About me", placeholder="""This can be anything that will help me pinpoint your request better, e.g.,  what kind of job you're looking for, where you're applying, etc.""")
            # st.markdown("Quick navigation")
            # with st.form( key='my_form', clear_on_submit=True):

            # col1, col2= st.columns([5, 5])

            # with col1:
            #     st.text_area(
            #         "Job",
            #         "",
            #         key="job",
            #         placeholder="job title or program name",                  
            #         on_change=self.form_callback,
            #     )
            
            # with col2:
            #     st.text_area(
            #         "Company",
            #         "",
            #         key = "company",
            #         placeholder="name of the company or institution",
            #         on_change=self.form_callback
            #     )
            
        # Chat section
        ## Displays the current conversation

        # if st.session_state['responses']:
        #     for i in range(len(st.session_state['responses'])):
        #         try:
        #             message(st.session_state['questions'][i], is_user=True, key=str(i) + '_user',  avatar_style="identicon", allow_html=True)
        #             message(st.session_state['responses'][i], key=str(i)+'_AI', logo="logo.png", seed="AI", allow_html=True)
        #         except Exception:
        #             pass   

        # self.callback_done = threading.Event()
        # thread = threading.Thread(target=self.question_callback, args=(self.callback_done, ))
        # add_script_run_ctx(thread, self.ctx)
        # thread.start()
        # c1, c2 = st.columns([2, 1])
        # User chat input area
        # c1.text_input("Chat with me: ",
        #             # value=st.session_state.prefilled, 
        #             key="input", 
        #             label_visibility="hidden", 
        #             placeholder="Chat with me",
        #             on_change = self.question_callback, 
        #             args = [self.callback_done],
        #             )
    
        # Select from sample questions
        # c2.selectbox(label="Sample questions",
        #             options=sorted(SAMPLE_QUESTIONS.keys()), 
        #             key = "prefilled",
        #             format_func=lambda x: '-----sample questions-----' if x == '' else x,
        #             label_visibility= "hidden",
        #             on_change = self.question_callback, 
        #             args = [self.callback_done],
        #             )

        # st.text_input("Chat with me: ", "", key="input", on_change = self.question_callback)
        # self.display_past_sessions()
        # self.retrieve_conversation()
        for msg in st.session_state.messages:
            st.chat_message(msg.role).write(msg.content)
        self.retrieve_downloads()      
            # for i in range(len(st.session_state['responses'])):
            #     try:
            #         st.chat_message("human").write(st.session_state['questions'][i])
            #         st.chat_message("ai").write(st.session_state['responses'][i])
            #     except Exception:
            #         pass  
        # Chat input
        # chat_input = st.chat_input(placeholder="Chat with me:",
        #                             key="input",)
        # Hacky way to clear selectbox below
  
        # Select from sample questions
        # sample_questions=st.selectbo      # def switch_input():
        #     st.session_state.questionInput = st.session_state.prefilled
        #     st.session_state.prefilled = Nonex(label="Sample questions",
        #             options=sorted(SAMPLE_QUESTIONS.keys()), 
        #             key = "prefilled",
        #             format_func=lambda x: '-----sample questions-----' if x == '' else x,
        #             label_visibility= "hidden",
        #             on_change =switch_input, 
        #             )
        #TODO sample questions will change to frequently asked questions
        sample_questions = [
            "help me generate a cover letter", 
            "Evaluate my resume",
            "rewrite my resume using a new template",
            "tailor my document to a job position",
        ]
      
        # chat_input = st.chat_input(placeholder="Chat with me:",
                                    # key="input",)
        chat_input = stDatalist("Chat with me...", sample_questions, key=f"input_{str(st.session_state.input_counter)}")
        # if prompt := chat_input or st.session_state.questionInput:
        if prompt := chat_input:
            # self.question_callback(prompt)
            st.session_state.messages.append(ChatMessage(role="user", content=prompt))
            # st.session_state.questionInput=None
            st.chat_message("human").write(prompt)
            # st.session_state.questions.append(prompt)
            self.question = prompt
            # Note: new messages are saved to history automatically by Langchain during run
            # with st.session_state.spinner_placeholder, st.spinner("Please wait..."):
            # question = self.process_user_input(prompt)
            # queue = Queue()
            # task = threading.Thread(
            #     target=self.new_chat.askAI,
            #     args=(st.session_state.sessionId,prompt)
            # )
            # task.start()
            container = st.empty()
            streamHandler = StreamHandler(container)
            response = self.new_chat.askAI(prompt, callbacks=streamHandler)

            # response = self.new_chat.askAI(st.session_state.sessionId, prompt,)
            if response == "functional" or response == "chronological" or response == "student":
                self.resume_template_popup(response)
            else:
                # st.chat_message("ai").write(response)
                # st.session_state.responses.append(response)
                st.session_state.messages.append(ChatMessage(role="assistant", content=response))
                self.response = response
            st.session_state["input_counter"] += 1

       
 



    # @st.cache_data(experimental_allow_widgets=True)
    # def about_me_popup(_self) -> None:
    
    #     """ Processes user's about me input. """

    #     modal = Modal(title="Let me know you a little better", key="about_popup", max_width=800)
    #     placeholder = st.empty()
    #     if st.session_state.get("past", False) and st.session_state.get("present", False) and st.session_state.get("future", False) :
    #         st.session_state.disabled=False
    #     else:
    #         st.session_state.disabled=True
    #     with placeholder.container():
    #         with modal.container():
    #             selected = stx.stepper_bar(steps=["Self Description", "Current Situation", "Career Goals"])
    #             if selected==0:
    #                 st.text_input(
    #                 label="What can I know about you?", 
    #                 placeholder="Tell me about yourself", 
    #                 key = "about_past", 
    #                 on_change=_self.about_me_form_check
    #                 )
    #             elif selected==1:
    #                 st.text_input(
    #                 label="What takes you here?",
    #                 placeholder = "Tell me about your present situation",
    #                 key="about_present",
    #                 on_change = _self.about_me_form_check
    #                 )
    #             elif selected==2:
    #                 st.text_input(
    #                 label="What can I do for you?",
    #                 placeholder = "Tell me about your career goals",
    #                 key="about_future",
    #                 on_change=_self.about_me_form_check,
    #                 )
    #             submitted = st.button("Submit", on_click=_self.form_callback, disabled=st.session_state.disabled)
    #             if submitted:
    #                  save_user_info(st.session_state.dnm_table, _self.userId, "self description", st.session_state.past)
    #                  st.rerun()

                
        
    # def about_me_form_check(self):

    #     # Hacky way to save input text for stepper bar for batch submission
    #     try:
    #         st.session_state["past"] = st.session_state.about_past
    #     except AttributeError:
    #         pass
    #     try:
    #         st.session_state["present"] = st.session_state.about_present
    #     except AttributeError:
    #         pass
    #     try:
    #         st.session_state["future"] = st.session_state.about_future
    #     except AttributeError:
    #         pass
    
   
    





    # def question_callback(self, prompt):
        
    #     prompt = prompt if prompt is not None else st.session_state.prefilled   
    #     st.chat_message("human").write(prompt)
    #     st.session_state.questions.append(prompt)
    #     # Note: new messages are saved to history automatically by Langchain during run
    #     # with st.session_state.spinner_placeholder, st.spinner("Please wait..."):
    #     question = self.process_user_input(prompt)
    #     response = self.new_chat.askAI(st.session_state.userid, question,)
    #     if response == "functional" or response == "chronological" or response == "student":
    #         self.resume_template_popup(response)
    #     else:
    #         st.chat_message("ai").write(response)
    #         st.session_state.responses.append(response)
    

        



    # def question_callback(self, callback_done, append_question=True):

    #     """ Sends user input to chat agent. """

    #     question = None
    #     try:
    #         if st.session_state.input!="" or st.session_state.prefilled!="":
    #             callback_done.set() 
    #             question = st.session_state.input if st.session_state.input else st.session_state.prefilled      
    #     except Exception:
    #         pass
    #     callback_done.wait()
    #     if question is not None:
    #         response = None
    #         with st.session_state.spinner_placeholder, st.spinner("Please wait..."):
    #             question = self.process_user_input(question)
    #             response = self.new_chat.askAI(st.session_state.userid, question, callbacks = None)
    #             # response="functional"
    #         if response == "functional" or response == "chronological" or response == "student":
    #             self.resume_template_popup(response)
    #         elif response:
    #             if append_question:
    #                 st.session_state.questions.append(question)
    #             st.session_state.responses.append(response)
    #         st.session_state.questionInput =  st.session_state.input if st.session_state.input else st.session_state.prefilled  
    #         st.session_state.input = ''    
    #         st.session_state.prefilled = ''
    


    # def file_upload_popup(self, callback_msg=""):

    #     """Popup for user to upload files. """

    #     # modal = Modal(title="Upload your files", key="file_popup", max_width=600)
    #     placeholder = st.empty()
    #     if "file_modal" not in st.session_state:
    #         st.session_state["file_modal"] =  Modal(title="    ", key="file_popup", max_width=600)
    #     with placeholder.container():
    #         with st.session_state.file_modal.container():
    #             st.write(callback_msg)
    #             if "file_loading" not in st.session_state:
    #                 st.session_state["file_loading"]=st.empty()
    #             col1, _ = st.columns([10, 1])
    #             with col1:
    #                 with st.form(key='file_popup_form', clear_on_submit=True):
    #                     # add_vertical_space(1)
    #                     st.file_uploader(
    #                         label="Upload your resume, cover letter, or anything you want to share with me.",
    #                         type=["pdf","odt", "docx","txt", "zip", "pptx"], 
    #                         key = "files",
    #                         # help = "This can be your resume, cover letter, or anything else you want to share with me. ",
    #                         label_visibility="hidden",
    #                         accept_multiple_files=True
    #                         )
    #                     # add_vertical_space(1)
    #                     st.form_submit_button(label='Submit', on_click=self.form_callback)  


    # def link_share_popup(self, callback_msg=""):

    #     """Popup for user to share url. """
    
    #     # modal = Modal(title="Share a link", key="link_popup", max_width=500)
    #     # placeholder=st.empty()
    #     if "link_modal" not in st.session_state:
    #         st.session_state["link_modal"] =  Modal(title="   ", key="link_popup", max_width=500)
    #     with placeholder.container():
    #         with st.session_state.link_modal.container():
    #             st.write(callback_msg)
    #             if "link_loading" not in st.session_state:
    #                 st.session_state["link_loading"]=st.empty()
    #             col1, _ = st.columns([10, 1])
    #             with col1:
    #                 with st.form(key="link_popup_form", clear_on_submit=True):
    #                     st.text_area(
    #                         label="", 
    #                         placeholder="This can be a job posting url for example", 
    #                         key = "links", 
    #                         # label_visibility="hidden",
    #                         help="If the link does not work, try saving the content and upload it as a file.",
    #                         )
    #                     st.form_submit_button(label="Submit", on_click=self.form_callback)

    # def retrieve_conversation(self):

    #     """ Displays a conversation on main screen. """

    #     if self.userId is not None:
    #         print(f"{self.userId} logged in")
    #         # save chat conversation if user logged in
    #         try:
    #             save_current_conversation(st.session_state.dnm_table, self.userId, self.question, self.response)
    #         except AttributeError:
    #             pass
    #             # st.session_state.responses.extendleft(ai)
    #             # st.session_state.questions.extendleft(human)
    #     for msg in st.session_state.messages:
    #         st.chat_message(msg.role).write(msg.content)


            # if st.session_state["current_session"] == st.session_state["sessionId"]:
            #     ai = st.session_state["responses"]
            #     human =  st.session_state["questions"]
            # else:
            #     ai = st.session_state["past_responses"]
                # human = st.session_state["past_questions"]
            # if human:
            #     for i in range(len(ai)):
            #         try:
            #             st.chat_message("human").write(human[i])
            #             st.chat_message("ai").write(ai[i])
            #         except Exception:
            #             pass  
        
    def retrieve_downloads(self):

        """ Displays AI generated files in sidebar downloads tab, if available, of the current session. """
        
        # files = self.check_user_downloads(st.session_state["current_session"])
        files = self.check_user_downloads()
        with st.session_state.download_placeholder.container():
            if files:
                for file in files:
                    st.markdown(self.binary_file_downloader_html(file), unsafe_allow_html=True)
            else:
                st.write("AI generated files will be shown here")

    # def display_past_sessions(self):

    #     """ Displays past sessions in sidebar tab. """

    #     with st.session_state.past_placeholder.container():
    #         if self.cookie is not None:
    #             if "past_human_sessions" not in st.session_state:
    #                 human, ai, ids = self.retrieve_sessions()
    #                 st.session_state["past_human_sessions"] = human
    #                 st.session_state["past_ai_sessions"] = ai
    #                 st.session_state["session_displays"] = ",".join(ids)
    #             if st.session_state.past_human_sessions:
    #                 # replace the display of time of current session witht the word current
    #                 st.session_state.session_displays.replace(st.session_state.sessionId, "current")
    #                 selected_idx = my_component(st.session_state.session_displays, key=f"session")
    #                 if selected_idx!=-1:
    #                     st.session_state["current_session"]= st.session_state.session_displays.split(",")[selected_idx]
    #                     print(st.session_state.current_session)
    #                     st.session_state["past_responses"] = st.session_state.past_ai_sessions[selected_idx]
    #                     print(st.session_state.past_responses)
    #                     st.session_state["past_questions"] = st.session_state.past_human_sessions[selected_idx]
    #             else:
    #                 st.write("No past sessions")
    #                 st.session_state["current_session"]=st.session_state.sessionId
    #         else:
    #             st.session_state["current_session"]=st.session_state.sessionId
    #             st.write("Please sign in or sign up to see past sessions")





 
    def form_callback(self):

        """ Processes form information after form submission. """
   
        try:
            # files = st.session_state.files 
            file_key = f"files_{str(st.session_state.file_counter)}"
            files = st.session_state[file_key]
            if files:
                self.process_uploads(files, "files")
                st.session_state["file_counter"] += 1
                # st.session_state.files=""
        except Exception:
            pass
        try:
            links = st.session_state.links
            if links:
                self.process_uploads(links, "links")
                st.session_state.links=""
        except Exception:
            pass
        try:
            about_job = st.session_state.aboutJob
            if about_job:
                self.new_chat.update_entities(f"about_job:{about_job} /n"+"~~~~", '~~~~')
                st.session_state.aboutJob=""
                st.toast("successfully submitted")
        except Exception:
            pass

        ## Passes the previous user question to the agent one more time after user uploads form
        # try:
        #     # print(f"QUESTION INPUT: {st.session_state.questionInput}")
        #     if st.session_state.questionInput!="":
        #         st.session_state.input = st.session_state.questionInput
        #         self.question_callback(self.callback_done, append_question=False)
        # # 'Chat' object has no attribute 'question': exception occurs when user has not asked a question, in this case, pass
        # except AttributeError:    
        #    pass


    # # @st.cache_data(experimental_allow_widgets=True)
    def resume_template_popup(_self, resume_type:str):

        """ Popup window for user to select a resume template based on the resume type. """

        modal = Modal(key="template_popup", title=f"Pick a template", max_width=1000)
        with modal.container():
            with st.form( key='template_form', clear_on_submit=True):
                template_idx = my_component(resume_type, "templates")
                st.form_submit_button(label='Submit', on_click=_self.resume_template_callback, args=[resume_type])

                            


    def resume_template_callback(self, resume_type:str):

        """ Calls the resume_rewriter tool to rewrite the resume according to the chosen resume template. """

        template_idx = st.session_state.templates
        print(f"TEMPLATE IDX:{template_idx}")
        resume_template_file = os.path.join(st.session_state.template_path,resume_type, f"{resume_type}{template_idx}.docx")
        question = f"""Please help user rewrite their resume using the resume_rewriter tool with the following resume_template_file:{resume_template_file}. """
        response = self.new_chat.askAI(st.session_state.sessionId, question, callbacks=None,)
        return st.session_state.responses.append(response)
        # self.question_callback(self.callback_done, append_question=False)



                
    def process_user_input(self, user_input: str) -> str:

        """ Processes user input and processes any links in the input. """

        #process url in input
        urls = re.findall(r'(https?://\S+)', user_input)
        print(urls)
        if urls:
            for url in urls:
                self.process_link(url)
        #tag user input content
        tag_schema = {
            "properties": {
                # "aggressiveness": {
                #     "type": "integer",
                #     "enum": [1, 2, 3, 4, 5],
                #     "description": "describes how aggressive the statement is, the higher the number the more aggressive",
                # },
                "topic": {
                    "type": "string",
                    "enum": ["question or answer", "career goals", "job or program description", "company or institution description"],
                    "description": "determines if the statement contains certain topic",
                },
            },
            # "required": ["topic", "sentiment", "aggressiveness"],
            "required": ["topic"],
        }
        response = create_input_tagger(tag_schema, user_input)
        topic = response.get("topic", "")
        # if topic == "upload files":
        #     self.file_upload_popup()
        # else: 
        if topic == "career goals" or topic=="job or program description" or topic=="company or institution description":
            self.new_chat.update_entities(f"about_me:{user_input} /n"+"###", '###')
        return user_input
    




    # def process_about_me(self, about_me: str) -> None:
    
    #     """ Processes user's about me input for content type and processes any links in the description. """

    #     content_type = """a job or study related user request. """
    #     user_request = evaluate_content(about_me, content_type)
    #     # about_me_summary = get_completion(f"""Summarize the following about me, if provided, and ignore all the links: {about_me}. """)
    #     self.new_chat.update_entities(f"about me:{about_me_summary} /n ###")
    #     if user_request:
    #         self.question = about_me
    #     urls = re.findall(r'(https?://\S+)', about_me)
    #     print(urls)
    #     if urls:
    #         for url in urls:
    #             self.process_link(url)

    def process_uploads(self, uploads: Any, upload_type: str) -> None:

        """Processes user uploads including converting all format to txt, checking content safety, content type, and content topics. 

        Args:
            
            uploads: files or links saved when user uploads on Streamlit
            
            upload_type: "files" or "links"
    
        """

        end_paths = []
        if upload_type=="files":
            for uploaded_file in uploads:
                file_ext = Path(uploaded_file.name).suffix
                filename = str(uuid.uuid4())+file_ext
                tmp_save_path = os.path.join(st.session_state.temp_path, st.session_state.sessionId, filename)
                end_path =  os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads", Path(filename).stem+'.txt')
                # if st.session_state.storage=="LOCAL":
                #     with open(tmp_save_path, 'wb') as f:
                #         f.write(uploaded_file.getvalue())
                # elif st.session_state.storage=="CLOUD":
                #     st.session_state.s3_client.put_object(Body=uploaded_file.getvalue(), Bucket=st.session_state.bucket_name, Key=tmp_save_path)
                #     print("Successful written file to S3")
                write_file(uploaded_file.getvalue(), tmp_save_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                if convert_to_txt(tmp_save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                    end_paths.append(end_path)
        elif upload_type=="links":
            end_path = os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads", str(uuid.uuid4())+".txt")
            links = re.findall(r'(https?://\S+)', uploads)
            if html_to_text(links, save_path=end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                end_paths.append(end_path)
        for end_path in end_paths:
            content_safe, content_type, content_topics = check_content(end_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
            print(content_type, content_safe, content_topics) 
            if content_safe and content_type!="empty" and content_type!="browser error":
                self.update_entities(content_type, content_topics, end_path)
                st.toast(f"your {content_type} is successfully submitted")
            else:
                delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                st.toast(f"Failed processing your material. Please try again!")




    # def process_file(self, uploaded_files: Any) -> None:

    #     """ Processes user uploaded files including converting all format to txt, checking content safety, and categorizing content type  """
    #     # with st.session_state.file_loading, st.spinner("Processing..."):
    #     # with st.session_state.spinner_placeholder, st.spinner("Processing..."):
    #     for uploaded_file in uploaded_files:
    #         file_ext = Path(uploaded_file.name).suffix
    #         filename = str(uuid.uuid4())+file_ext
    #         tmp_save_path = os.path.join(st.session_state.temp_path, st.session_state.sessionId, filename)
    #         end_path =  os.path.join(st.session_state.save_path, st.session_state.sessionId, "chat", "uploads", Path(filename).stem+'.txt')
    #         if st.session_state.storage=="LOCAL":
    #             with open(tmp_save_path, 'wb') as f:
    #                 f.write(uploaded_file.getvalue())
    #         elif st.session_state.storage=="CLOUD":
    #             st.session_state.s3_client.put_object(Body=uploaded_file.getvalue(), Bucket=st.session_state.bucket_name, Key=tmp_save_path)
    #             print("Successful written file to S3")
    #         # Convert file to txt and save it 
    #         convert_to_txt(tmp_save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client) 
    #         content_safe, content_type, content_topics = check_content(end_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #         print(content_type, content_safe, content_topics) 
    #         if content_safe and content_type!="empty":
    #             self.update_entities(content_type, content_topics, end_path)
    #             st.toast(f"your {content_type} is successfully submitted")
    #         else:
    #             delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #             delete_file(tmp_save_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #             st.toast(f"Failed processing {Path(uploaded_file.name).root}. Please try another file!")
    #             # self.file_upload_popup(callback_msg=f"Failed processing {Path(uploaded_file.name).root}. Please try another file!")
        
        

    # def process_link(self, links: Any) -> None:

    #     """ Processes user shared links including converting all format to txt, checking content safety, and categorizing content type """
    #     # with st.session_state.link_loading, st.spinner("Processing..."):
    #     # with st.session_state.spinner_placeholder, st.spinner("Processing..."):
    #     end_path = os.path.join(st.session_state.save_path, st.session_state.sessionId, "chat", "uploads", str(uuid.uuid4())+".txt")
    #     links = re.findall(r'(https?://\S+)', links)
    #     if html_to_text(links, save_path=end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
    #         content_safe, content_type, content_topics = check_content(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #         print(content_type, content_safe, content_topics) 
    #         if (content_safe and content_type!="empty" and content_type!="browser error"):
    #             self.update_entities(content_type,content_topics, end_path)
    #             st.toast(f"your {content_type} is successfully submitted")
    #         else:
    #             #TODO: second browser reader for special links such as the OnlinePDFReader: https://python.langchain.com/docs/modules/data_connection/document_loaders/pdf
    #             delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #             st.toast(f"Failed processing {str(links)}. Please try another link!")
    #             # self.link_share_popup(callback_msg=f"Failed processing {str(links)}. Please try another link!")
    #     else:
    #         st.toast(f"Failed processing {str(links)}. Please try another link!")
    #         # self.link_share_popup(callback_msg=f"Failed processing {str(links)}. Please try another link!")



    def update_entities(self, content_type:str, content_topics: set[str], end_path:str) -> None:

        """ Adds entities to chat agent. 
        
        Args:

            content_type: file's content categorized as one of the following ["empty", "resume", "cover letter", "job posting", "education program", "personal statement", "browser error", "learning material", "other"]

            content_topics: topics of the content, if available, for learning material specifically
            
            end_path: file path
            
        """

        if content_type!="other" and content_type!="learning material":
            delimiter=""
            if content_type=="job posting":
                delimiter = "@@@"
            elif content_type=="resume":
                delimiter = "$$$"    
            if content_type=="job posting":
                content = read_txt(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name,s3=st.session_state.s3_client)
                token_count = num_tokens_from_text(content)
                if token_count>max_token_count:
                    shorten_content(end_path, content_type) 
            content_type = content_type.replace(" ", "_").strip()
            entity = f"""{content_type}_file: {end_path} /n"""+delimiter
            self.new_chat.update_entities(entity, delimiter)
        if content_type=="learning material" :
            # update user material, to be used for "search_user_material" tool
            delimiter = "###"
            record_name = self.userId if self.userId is not None else st.session_state.sessionId
            vs_path = user_vs_name if st.session_state.storage=="CLOUD" else os.path.join(st.session_state.save_path, st.session_state.sessionId, user_vs_name)
            update_vectorstore(end_path=end_path, vs_path =vs_path,  index_name=user_vs_name, record_name=record_name, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
            entity = f"""user_material_path: {vs_path} /n"""+delimiter
            self.new_chat.update_entities(entity, delimiter)
            if content_topics:
                delimiter = "###"
                topics = ", ".join(content_topics)
                entity = f"""user_material_topics: {topics} /n"""+delimiter
                self.new_chat.update_entities(entity, delimiter)


    # def update_vectorstore(self, end_path: str) -> str:

    #     """ Creates and updates vector store for chat agent to be used as RAG. 
        
    #     Args:
        
    #         end_path: path to file
            
    #     Returns:
        
    #         path or index name of vectot store
            
    #     """
    #     if st.session_state.storage=="LOCAL":
    #         vs_name = "user_material"
    #         vs = merge_faiss_vectorstore(vs_name, end_path)
    #         vs_path =  os.path.join(st.session_state.save_path, st.session_state.sessionId, vs_name)
    #         vs.save_local(vs_path) 
    #     elif st.session_state.storage=="CLOUD":
    #         index_name=f"user_material"
    #         docs = split_doc_file_size(end_path, "file", storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #         vectorstore = retrieve_vectorstore("elasticsearch", index_name=index_name)
    #         record_manager=create_record_manager(self.userId if self.userId is not None else st.session_state.sessionId)
    #         if vectorstore is None:
    #             vectorstore = create_vectorstore(vs_type="elasticsearch", 
    #                             index_name=index_name, 
    #                             )
    #         update_index(docs=docs, record_manager=record_manager, vectorstore=vectorstore, cleanup_mode=None)
    #         vs_path=index_name
    #     return vs_path

    def binary_file_downloader_html(self, file: str) -> str:

        """ Creates the download link for AI generated file. 
        
        Args: 
        
            file: file path
            
        Returns:

            a link tag that includes the href to the file location   

        """

        # if st.session_state.storage=="LOCAL":
        #     with open(file, 'rb') as f:
        #         data = f.read() 
        # elif st.session_state.storage=="CLOUD":
        #     object = st.session_state.s3_client.get_object(Bucket=st.session_state.bucket_name, Key=file)
        #     data = object['Body'].read()
        data = read_file(file, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
        bin_str = base64.b64encode(data).decode() 
        href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(file)}">Download Link</a>'
        return href
    
    # def save_current_session(self):

    #     """ Saves chat session. """
  
    #     chat = self.new_chat.conversation
    #     user = st.session_state.dnm_table.get_item(
    #         Key={'userId': st.session_state.userId},

    #     )
    #     if 'Item' in user:
    #         # append session info
    #         info = [{"sessionId": st.session_state.sessionId, "human":chat["human"], "ai":chat["ai"]}]
    #         # st.session_state.dnm_table.update_item(
    #         #     Key={"userId": st.session_state.userId},
    #         #     UpdateExpression="set info = list_append(info, :n)",
    #         #     ExpressionAttributeValues={
    #         #         ":n": info,
    #         #     },
    #         #     ReturnValues="UPDATED_NEW",
    #         # )
    #         st.session_state.dnm_table.update_item(
    #             Key={"userId": st.session_state.userId},
    #             UpdateExpression="set human = list_append(human, :n)",
    #             ExpressionAttributeValues={
    #                 ":n": chat["human"],
    #             },
    #             ReturnValues="UPDATED_NEW",
    #         )
    #         st.session_state.dnm_table.update_item(
    #             Key={"userId": st.session_state.userId},
    #             UpdateExpression="set ai = list_append(ai, :n)",
    #             ExpressionAttributeValues={
    #                 ":n": chat["ai"],
    #             },
    #             ReturnValues="UPDATED_NEW",
    #         )
    #         print("APPENDING OLD USER TO TABLE")
    #     else:
    #     # except Exception:
    #         # put new user into table
    #         # info = [{"sessionId": st.session_state.sessionId, "human":chat["human"], "ai":chat["ai"]}]
    #         # st.session_state.dnm_table.put_item(
    #         #     Item = {
    #         #         "userId": st.session_state.userId,
    #         #         "info": info,
    #         #     },
    #         # )
    #         st.session_state.dnm_table.put_item(
    #             Item = {
    #                 "userId": st.session_state.userId,
    #                 "human": chat["human"],
    #                 "ai" : chat["ai"]
    #             },
    #         )
    #         print("ADDING NEW USER TO TABLE")


    # def retrieve_sessions(self) -> Union[List[str], List[str], List[str]]: 

    #     """ Returns past chat sessions associated with user"""

    #     human, ai, ids = [], [], []
    #     try:
    #         response = st.session_state.dnm_table.query(
    #             KeyConditionExpression=Key('userId').eq(st.session_state.userId)),
    #         print(response)
    #         # session_info = response[0]['Items'][0]['info']
    #         session_info = response[0]['Items'][0]
    #         for item in session_info:
    #             human.append(item["human"])
    #             ai.append(item["ai"])
    #             # ids.append(item["sessionId"])
    #     except Exception:
    #         pass
    #     return human, ai, ids



    # @st.cache_resource()
    def check_user_downloads(self) -> List[str]:

        """ Checks AI generated files in download folder and returns a list of file paths. """

        download_dir = os.path.join(st.session_state.save_path, st.session_state.sessionId, "downloads")
        generated_files = []
        if st.session_state.storage=="LOCAL":
            try:
                for path in Path(download_dir).glob('**/*.docx*'):
                    file=str(path)
                    print(f"DOWNLOAD FILE: {file}")
                    generated_files.append(file)
            except Exception:
                pass
        elif st.session_state.storage=="CLOUD":
            try:
                response = st.session_state.s3_client.list_objects(Bucket=st.session_state.bucket_name, Prefix=download_dir)
                for content in response.get('Contents', []):
                    file=content.get['Key']
                    if Path(file).suffix==".docx":
                        generated_files.append(file)
            except Exception:
                pass
        return generated_files

    
class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        # self.container.markdown(self.text)
        with self.container.container():
            st.chat_message("ai").write(self.text)




if __name__ == '__main__':

    advisor = Chat()
    # asyncio.run(advisor.initialize())
