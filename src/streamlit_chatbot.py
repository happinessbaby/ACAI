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
from backend.career_advisor import ChatController
# from callbacks.capturing_callback_handler import playback_callbacks
from utils.basic_utils import convert_to_txt, read_txt, retrieve_web_content, html_to_text, delete_file, mk_dirs, write_file, read_file
from utils.openai_api import get_completion, num_tokens_from_text, check_content_safety
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  check_content, evaluate_content, generate_tip_of_the_day, shorten_content
import re
from typing import Any, List, Union
import multiprocessing as mp
from utils.langchain_utils import (merge_faiss_vectorstore, create_input_tagger, create_vectorstore, update_vectorstore)
import openai
import json
# from st_pages import show_pages_from_config, add_page_title, show_pages, Page, Section
# from st_clickable_images import clickable_images
# from st_click_detector import click_detector
# from streamlit_extras.switch_page_button import switch_page
from streamlit_modal import Modal
import base64
from langchain.tools import tool
import streamlit.components.v1 as components, html
from PIL import Image
from interview_component import my_component
# from thread_safe_st import ThreadSafeSt
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from langchain.callbacks.base import BaseCallbackHandler
import threading
import queue
import time
from utils.cookie_manager import get_cookie, decode_jwt
from utils.aws_manager import get_client, request_aws4auth
# from st_multimodal_chatinput import multimodal_chatinput
# from streamlit_datalist import stDatalist
import time
import re
from langchain.schema import ChatMessage
# from st_click_detector import click_detector
from st_btn_select import st_btn_select
from backend.generate_cover_letter import generate_preformatted_cover_letter, generate_basic_cover_letter


_ = load_dotenv(find_dotenv()) # read local .env file

# Either this or add_indentation() MUST be called on each page in your
# app to add indendation in the sidebar

# Optional -- adds the title and icon to the current page
# add_page_title()

# Specify what pages should be shown in the sidebar, and what their titles and icons
# should be


# show_pages(
#     [
#         Page("streamlit_user.py", f"User"),
#         Section(name="Settings"),
#         Page("streamlit_chatbot.py", "Career Help", "🏠"),
#         Page("streamlit_interviewbot.py", "Mock Interview", ":books:"),
#         # Page("streamlit_resources.py", "My Journey", ":busts_in_silhouette:" ),
#     ]
# )

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
st.markdown("<style> ul {display: none;} </style>", unsafe_allow_html=True)


class Chat():

    ctx = get_script_run_ctx()
    # chatinput = multimodal_chatinput()

    
    def __init__(self):

        # NOTE: userId is retrieved from browser cookie
        self.cookie = get_cookie("userInfo")
        if self.cookie:
            self.userId = decode_jwt(self.cookie, "test").get('username')
            print("Cookie:", self.userId)
        else:
            self.userId = None
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states()
        self._create_chatbot()
        self._init_display()

        

    # NOTE: Cache differently depending on if user is logged in and re-caches for each new session
    @st.cache_data()
    def _init_session_states(_self,):

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
        st.session_state["resume_modal"]= Modal("", key="resume_modal", max_width="600" )
        st.session_state["cover_letter_modal"]= Modal("", key="cover_leter_modal", max_width="600" )
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
        # if _self.userId is not None:
        #     # if "dnm_table" not in st.session_state:
        #     st.session_state["dnm_table"] = init_table(session=_self.aws_session, userId=_self.userId)
           

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
            st.session_state["s3_client"]= get_client('s3') 
            # st.session_state["awsauth"] = request_aws4auth(_self.aws_session)
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
        # st.session_state["selected"]=None 
        if st.session_state.cover_letter_modal.is_open():
            print("cover letter modal is open")
            _self.cover_letter_popup()
        if st.session_state.resume_modal.is_open():
            _self.resume_popup()
        with st._main:

            # if "initial_resume" not in st.session_state:
            #         #TODO: logged in user can select from past resume
            #     modal=Modal("Welcome", key="welcome_modal", close_button=False, max_width="600" )
            #     with modal.container():
            #         # with st.form(key="resume_form"):
            #         file= st.file_uploader(label="Upload your most recent resume", 
            #                                key="resume",
            #                                 type=["pdf","odt", "docx","txt"], 
            #                                 on_change=_self.form_callback)
            #             # st.form_submit_button("Submit", on_click=_self.form_callback,)
            #         skip = st.button("next", key="skip_resume_button", type="primary")
            #         if skip:
            #             st.session_state["initial_resume"]=False
            #             st.rerun()

            # elif "initial_resume" in st.session_state:
                st.markdown("<h1 style='text-align: center; color: black;'>Welcome</h1>", unsafe_allow_html=True)
                st.markdown("#")
                st.markdown("<h3 style='text-align: center; color: black ;'> Let AI empower your career building journey</h3>", unsafe_allow_html=True)
                st.markdown("#")
                st.session_state["selected"] = st_btn_select(('Resume', "Cover letter",'Mock interview', "Job search", "Profile", ""), index=-1, key="btn_selection")
                if st.session_state.selected=="Resume":
                    st.session_state.resume_modal.open()
                elif st.session_state.selected=="Cover letter":
                    # st.session_state.cover_letter_modal.open()
                    _self.cover_letter_popup()
                if st.session_state.selected=="Mock interview":
                    st.switch_page("pages/streamlit_interviewbot.py")
                elif st.session_state.selected=="Profile":
                    st.switch_page("pages/streamlit_user.py")
                elif st.session_state.selected=="Job search":
                    st.switch_page("pages/streamlit_jobs.py")
            # for msg in st.session_state.messages:
            #     st.chat_message(msg.role).write(msg.content)
        
            # chat_input = st.chat_input(placeholder="Chat with me:",key="input", on_submit=_self.chat_callback)
  


            # chat_input = stDatalist("Chat with me...", sample_questions, key=f"input_{str(st.session_state.input_counter)}")
            # if prompt := chat_input or st.session_state.questionInput:
            # if prompt := chat_input:
            #     # self.question_callback(prompt)
            #     st.session_state.messages.append(ChatMessage(role="user", content=prompt))
            #     # st.session_state.questionInput=None
            #     st.chat_message("human").write(prompt)
            #     # st.session_state.questions.append(prompt)
            #     _self.question = prompt
            #     # Note: new messages are saved to history automatically by Langchain during run
            #     # with st.session_state.spinner_placeholder, st.spinner("Please wait..."):
            #     # question = self.process_user_input(prompt)
            #     # queue = Queue()
            #     # task = threading.Thread(
            #     #     target=self.new_chat.askAI,
            #     #     args=(st.session_state.sessionId,prompt)
            #     # )
            #     # task.start()
            #     # container = st.empty()
            #     # streamHandler = StreamHandler(container)
            #     response = _self.new_chat.askAI(prompt,)

            #     # response = self.new_chat.askAI(st.session_state.sessionId, prompt,)
            #     if response == "functional" or response == "chronological" or response == "student":
            #         _self.resume_template_popup(response)
            #     else:
            #         # st.chat_message("ai").write(response)
            #         # st.session_state.responses.append(response)
            #         st.session_state.messages.append(ChatMessage(role="assistant", content=response))
            #         _self.response = response
            #     st.session_state["input_counter"] += 1  

        # with st.sidebar:
        #     add_vertical_space(5)

        #     with st.expander("Upload & Share"):
        #         st.file_uploader(label="Files",
        #                         accept_multiple_files=True,
        #                         help = "This can be a resume, cover letter, job posting, study material, etc.",
        #                         key= f"files_{str(st.session_state.file_counter)}",
        #                         on_change=_self.form_callback)
        #         link = st.checkbox("job posting link")
        #         description = st.checkbox("job description")
        #         if link:
        #             st.text_area(label="Links", 
        #                     placeholder="This can be a job posting site for example", 
        #                     key = "links", 
        #                     # label_visibility="hidden",
        #                     help="If the link failed, please try to save the content into a file and upload it.",
        #                 on_change=_self.form_callback)
        #         if description:
        #             st.text_area(label="About",
        #                         key="aboutJob",
        #                         placeholder="What should I know about this job?",
        #                         on_change=_self.form_callback)
        #     with st.expander("Download your files"):
        #         if "download_placeholder" not in st.session_state:
        #             st.session_state["download_placeholder"]=st.empty()
        #         _self.retrieve_downloads()  
            # with st.expander("Commonly asked questions"):
            # st.markdown("Commonly asked questions")
            # sample_questions =[
            #     "hi",
            # "Evaluate my resume",
            # "Rewrite my resume using a new template",
            # "Tailor my resume to a job position",
            # ]
            # content = f"""<p><a href='#' id='0'>{sample_questions[0]}</a></p>
            #     <p><a href='#' id='1'>{sample_questions[1]}</a></p>
            #     <p><a href='#' id='1'>{sample_questions[2]}</a></p>
            #     <p><a href='#' id='1'>{sample_questions[3]}</a></p>
            #     """
            # clicked = click_detector(content, key=f"clickable_question")
            # if clicked:
            #     _self.chat_callback(clicked)
                # st.markdown(f"**{clicked} clicked**" if clicked != "" else "**No click**")
                # question = st.selectbox("", index=None, key="prefilled", options=sample_questions,)
                # if question:
                #     _self.chat_callback(question)
        # if cover_letter_modal.is_open():
        #     st.write("test")

    @st.experimental_dialog("Please fill out the form below")
    def cover_letter_popup(self,):
        
        # with st.session_state.cover_letter_modal.container():
        if "resume_path" not in st.session_state:
            st.session_state.resume_checkmark="*"
        if "job_posting_path" not in st.session_state and "job_description" not in st.session_state:
            st.session_state.job_posting_checkmark="*"
        if "cl_type_selection" not in st.session_state:
            st.session_state.cl_type_checkmark="*"
        if "resume_path" in st.session_state and ("job_posting_path" in st.session_state or "job_description" in st.session_state) and "cl_type_selection" in st.session_state:
            st.session_state.cl_disabled=False
        else:
            st.session_state.cl_disabled=True
        resume= st.file_uploader(label=f"Upload your most recent resume {st.session_state.resume_checkmark}", 
                                key="resume",
                                type=["pdf","odt", "docx","txt"], 
                                # on_change=self.form_callback
                                )
        if resume:
            self.process_uploads([resume], "resume")
        job_posting = st.radio(f"Job posting {st.session_state.job_posting_checkmark}", key="job_posting_radio", options=["job description", "job posting link"])
        if job_posting=="job posting link":
            job_posting_link = st.text_input(label="Job posting link", 
                            key="job_posting", 
                        # on_change=self.form_callback
                            )
            if job_posting_link:
                self.process_uploads(job_posting_link, "job_posting")
        elif job_posting=="job description":
            job_description = st.text_area("Job description", key="job_descriptionx", value=st.session_state.job_description if "job_description" in st.session_state else "")
            if job_description:
                st.session_state.job_posting_checkmark="✅"
                st.session_state["job_description"] = job_description       
        selection = st.selectbox(f"How would you like your cover letter? {st.session_state.cl_type_checkmark}", ("pick from a template", "write a creative draft"), index=None, placeholder="Please make a selection..", key="cl_type_selectionx" )
        if selection:
            st.session_state.cl_type_checkmark="✅"
            st.session_state["cl_type_selection"]=selection
        conti = st.button("next", key="next_resume_button", type="primary", disabled=st.session_state.cl_disabled, on_click=self.selection_callback, args=("cover letter", ))


    def selection_callback(self, type, ):
        # self.form_callback()
        if type=="cover letter":
            if st.session_state.cl_type_selection == "pick from a template":
                generate_preformatted_cover_letter(st.session_state["resume_path"],
                                                    st.session_state["job_posting_path"] if "job_posting_path" in st.session_state else "", 
                                                    st.session_state["job_description"] if "job_description" in st.session_state else "")
                print("Successfully generated preformatted cover letter")
            elif st.session_state.cl_type_selection == "write a creative craft":
                generate_basic_cover_letter(resume_file=st.session_state["resume_path"], 
                                            posting_path = st.session_state["job_posting_path"] if "job_posting_path" in st.session_state else "", 
                                            about_job =  st.session_state["job_description"] if "job_description" in st.session_state else "")
                print("Successfully generated creative cover letter draft")

    def chat_callback(self, prompt):

        # prompt = st.session_state.prefilled if self.sample_question else st.session_state.input   
        st.session_state.messages.append(ChatMessage(role="user", content=prompt))
        # st.session_state.questionInput=None
        # st.chat_message("human").write(prompt)
        # st.session_state.questions.append(prompt)
        self.question = prompt
        # Note: new messages are saved to history automatically by Langchain during run
        # with st.session_state.spinner_placeholder, st.spinner("Please wait..."):
        # question = self.process_user_input(prompt)
        response = self.new_chat.askAI(prompt,)
        # response = self.new_chat.askAI(st.session_state.sessionId, prompt,)
        if response == "functional" or response == "chronological" or response == "student":
            self.resume_template_popup(response)
        else:
            # st.chat_message("ai").write(response)
            # st.session_state.responses.append(response)
            st.session_state.messages.append(ChatMessage(role="assistant", content=response))
            self.response = response
        st.rerun()
        

    def typewriter(self, text: str, speed=1): 

        """ Displays AI response playback at a particular speed. """

        tokens = text.split()
        container = st.empty()
        for index in range(len(tokens) + 1):
            curr_full_text = " ".join(tokens[:index])
            container.markdown(curr_full_text)
            time.sleep(1 / speed)


    def generate_common_questions(self):

        """ Generate a list of commone questions users ask """

        pass
                
  
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
            resume=st.session_state.resume
            if resume:
                print("User uploaded resume")
                self.process_uploads([resume],"resume" )
        except Exception:
            pass
        try:
            job_posting=st.session_state.job_posting
            if job_posting:
                st.session_state.job_posting=""
                self.process_uploads(job_posting, "job_posting")
        except Exception:
            pass
        # try:
        #     job_description=st.session_state.job_description
        #     if job_description:
        #         st.session_state["about_job"] = job_description
        # except Exception:
        #     pass
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
        if upload_type=="files" or upload_type=="resume":
            for uploaded_file in uploads:
                file_ext = Path(uploaded_file.name).suffix
                filename = str(uuid.uuid4())
                tmp_save_path = os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads", filename+file_ext)
                end_path =  os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads", filename+'.txt')
                if write_file(uploaded_file.getvalue(), tmp_save_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                    if convert_to_txt(tmp_save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                        if upload_type=="files":
                            end_paths.append(end_path)
                        elif upload_type=="resume":
                            content_safe, content_type, content_topics = check_content(end_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                            if content_safe and content_type=="resume":
                                st.session_state["resume_path"]= end_path
                                st.session_state.resume_checkmark="✅"
        elif upload_type=="job_posting":
            end_path = os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads", str(uuid.uuid4())+".txt")
            if html_to_text(uploads, save_path=end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                content_safe, content_type, content_topics = check_content(end_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                if content_safe and content_type=="job posting":
                    st.session_state["job_posting_path"]=end_path
                    st.session_state.job_posting_checkmark="✅"
            else:
                st.info("That didn't work. Please try pasting the content in job description instead.")
        elif upload_type=="links":
            links = re.findall(r'(https?://\S+)', uploads)
            if html_to_text(links, save_path=end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client):
                end_paths.append(end_path)
        for end_path in end_paths:
            content_safe, content_type, content_topics = check_content(end_path,  storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
            print(content_type, content_safe, content_topics) 
            # if content_safe and content_type!="empty" and content_type!="browser error":
            #     self.update_entities(content_type, content_topics, end_path)
            #     st.toast(f"your {content_type} is successfully submitted")
            if content_safe and content_type=="resume":
                 st.session_state["resume_path"]= end_path
            elif content_safe and content_type=="job posting":
                st.session_state["job_posting_path"]=end_path
            else:
                delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                st.toast(f"Failed processing your material. Please try again!")



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
