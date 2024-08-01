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
from utils.basic_utils import read_txt,delete_file, mk_dirs, write_file, read_file
from utils.openai_api import  num_tokens_from_text
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  generate_tip_of_the_day, shorten_content, retrieve_or_create_job_posting_info, retrieve_or_create_resume_info, process_uploads, process_links, process_inputs, match_resume_to_job
import re
from typing import Any, List, Union
import multiprocessing as mp
from utils.langchain_utils import update_vectorstore
import openai
import json
# from st_pages import show_pages_from_config, add_page_title, show_pages, Page, Section
# from st_clickable_images import clickable_images
# from st_click_detector import click_detector
# from streamlit_extras.switch_page_button import switch_page
# from streamlit_modal import Modal
# from thread_safe_st import ThreadSafeSt
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import time
from utils.cookie_manager import CookieManager
# from utils.aws_manager import get_client, request_aws4auth
# from st_multimodal_chatinput import multimodal_chatinput
# from streamlit_datalist import stDatalist
import time
import re
# from st_click_detector import click_detector
# from st_clickable_images import clickable_images
# from streamlit_simple_gallery import ImageGallery
from streamlit_image_select import image_select
from utils.aws_manager import get_aws_session,  get_client
from json.decoder import JSONDecodeError
from stqdm import stqdm
import threading
import queue
from utils.lancedb_utils import retrieve_user_profile_dict
from streamlit_utils import user_menu, set_streamlit_page_config_once
from css.streamlit_css import tabs
import multiprocessing
import streamlit as st
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import ChatMessage

set_streamlit_page_config_once()

_ = load_dotenv(find_dotenv()) # read local .env file

# Either this or add_indentation() MUST be called on each page in your
# app to add indendation in the sidebar

# Optional -- adds the title and icon to the current page
# add_page_title()

# Specify what pages should be shown in the sidebar, and what their titles and icons
# should be


# show_pages(
#     [
#         Page("user.py", f"User"),
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
user_profile_file=os.environ["USER_PROFILE_FILE"]
message_key = {
"PK": os.environ["PK"],
"SK": os.environ["SK"],
}
topic = "jobs"
resume_options = ["evaluate my resume", "redesign my resume with a new template", "tailor my resume to a job posting"]
interview_options=["phone interview", "panel interview"]
st.markdown("<style> ul {display: none;} </style>", unsafe_allow_html=True)



class Main():

    ctx = get_script_run_ctx()

    
    def __init__(self):


        if "cm" not in st.session_state:
            st.session_state["cm"] = CookieManager()
        self.userId = st.session_state.cm.retrieve_userId()
        # if self.userId:
        #     if "user_mode" not in st.session_state:
        #         st.session_state["user_mode"]="signedin" 
        #     st.session_state["user_profile_dict"]=retrieve_user_profile_dict(self.userId)
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states()
        # self._create_chatbot()
        self._init_display()

        

    @st.cache_data()
    def _init_session_states(_self,):

        """ Initializes Streamlit session states. """

        # try:
        #     st.session_state["users"]
        # except Exception:
        #     with open(user_profile_file, 'r') as file:
        #         try:
        #             st.session_state["users"] = json.load(file)
        #             st.session_state["users_dict"] = {user['userId']: user for user in st.session_state.users}
        #         except JSONDecodeError:
        #             raise
        # try:
        #     st.session_state["resume_dict"]=st.session_state["users_dict"][_self.userId]["resume_info_dict"]
        # except Exception:
        #     pass
        # _, c1 = st.columns([10, 1])
        # with c1:
        #     st.session_state["placeholder_profile"]=st.empty()
        # if "tip" not in st.session_state:
            # tip = generate_tip_of_the_day(topic)
            # st.session_state["tip"] = tip
            # st.write(tip)
        # if "messages" not in st.session_state:
        # st.session_state["messages"] = [ChatMessage(role="assistant", content="How can I help you?")]
        #TODO, get dynamodb message history to work
        # message_history = DynamoDBChatMessageHistory(table_name=_self.userId, session_id=st.session_state.sessionId, key=message_key, boto3_session=_self.aws_session)
        # st.session_state["message_history"]=None
        # st.session_state["resume_modal"]= Modal("", key="resume_modal", max_width="600" )
        # st.session_state["cover_letter_modal"]= Modal("", key="cover_leter_modal", max_width="600" )
        # new_chat = ChatController(st.session_state.sessionId, chat_memory=message_history)
        # st.session_state["basechat"] = new_chat
        ## hacky way to clear uploaded files once submitted
        # if "file_counter" not in st.session_state:
        # st.session_state["file_counter"] = 0
        # if "input_counter" not in st.session_state:
        # st.session_state["input_counter"] = 0
        # if "template_path" not in st.session_state:
        # st.session_state["template_path"] = os.environ["TEMPLATE_PATH"]
        # st.session_state["selections"] = st_btn_select(("Resume & Cover Letter",'Mock Interview', "Job Search", "My Profile", ""), index=-1,)
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
        # st.session_state["resume_placeholder"] = st.empty()
        # if STORAGE == "LOCAL":
        #     st.session_state["storage"]="LOCAL"
        #     st.session_state["bucket_name"]=None
        #     st.session_state["s3_client"]= None
        #     # if "save_path" not in st.session_state:
        #     if _self.userId is not None:
        #         st.session_state["save_path"] = os.path.join(os.environ["USER_PATH"], _self.userId, "main")
        #     else:
        #         st.session_state["save_path"] =os.environ["MAIN_PATH"]
        #     st.session_state["temp_path"]  = os.environ["TEMP_PATH"]
        # elif STORAGE=="CLOUD":
        #     st.session_state["storage"]="CLOUD"
        #     st.session_state["bucket_name"]=bucket_name
        #     st.session_state["s3_client"]= get_client('s3') 
        #     # st.session_state["awsauth"] = request_aws4auth(_self.aws_session)
        #     # if "save_path" not in st.session_state:
        #     if _self.userId is not None:
        #         st.session_state["save_path"] = os.path.join(os.environ["S3_USER_PATH"], _self.userId, "main")
        #     else:
        #         st.session_state["save_path"] =os.environ["S3_MAIN_PATH"]
        #     # if "temp_path" not in st.session_state:
        #     st.session_state["temp_path"]  = os.environ["S3_TEMP_PATH"]
        # paths = [st.session_state.save_path,
        #         os.path.join(st.session_state.temp_path, st.session_state.sessionId), 
        #         os.path.join(st.session_state.save_path, st.session_state.sessionId),
        #         # os.path.join(st.session_state.save_path, st.session_state.sessionId, "downloads"),
        #         os.path.join(st.session_state.save_path, st.session_state.sessionId, "uploads"),
        #         ]
        # mk_dirs(paths,)

   
    def _init_display(_self):

        """ Initializes UI. """

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



        # if "resume help" not in st.session_state and "match" not in st.session_state:
        #     if "resume_path" in st.session_state:
        #         del st.session_state["resume_path"]
        #     if "job_description" in st.session_state:
        #         del st.session_state["job_description"]
        #     if "job_posting_path" in st.session_state:
        #         del st.session_state["job_posting_path"]
        # else:
        #     _self.process_selection()
        #     if "resume help" in st.session_state and st.session_state["resume help"]:
        #         st.switch_page("pages/streamlit_dashboard.py")
        #     elif "match" in st.session_state and  st.session_state["match"]:
        #         match_resume_to_job()

        with st._main:
            st.switch_page("pages/user.py")
            # st.session_state["redirect_page"] =  "home.py"
            # user_menu(_self.userId, page="main")

            # st.markdown("<h1 style='text-align: center; color: #3ec0c8;'>Welcome</h1>", unsafe_allow_html=True)
            # add_vertical_space(5)
            # _, c1, c2=st.columns([1, 2,  2])
            # st.markdown(tabs, unsafe_allow_html=True)
            # resume, interview = st.tabs(["               Resume                  ", "                       Interview"])
            # with resume:
            #     if st.button("Resume Help", key="resume_button",):
            #         _self.resume_form_popup(job_required=False)
            # with interview:
            #     if st.button("Mock Interview", key="interview_button"):
            #         st.switch_page("pages/streamlit_interviewbot.py")
            # with c3:
            #     job_option = st.button("Job Search", key="job_button")
            # if job_option:
            #     st.switch_page("pages/streamlit_jobs.py")
            # add_vertical_space(5)
            # _, c2, _ = st.columns([1, 1, 1])
            # with c2:
            #     if st.button("Match Me!"):
            #         _self.general_form_popup(selection="match", job_required=True, resume_required=True,)
        

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
  




    @st.dialog(" ", )
    def resume_form_popup(self, resume_required=True, job_required = False, ):
        
        """ Form popup for resume help"""

        add_vertical_space(2)
        if ("resume_path" not in st.session_state and resume_required) or (("job_posting_path" not in st.session_state and "job_description" not in st.session_state) and (job_required or "job_required" in st.session_state)):
            st.session_state.conti_disabled=True
        else:
            st.session_state.conti_disabled=False
        if "resume_path" not in st.session_state:
            if resume_required:
                st.session_state.resume_checkmark=":red[(required)]"
            else:
                st.session_state.resume_checkmark="(optional)"
        if (("job_posting_path" not in st.session_state and "job_description" not in st.session_state) or ("job_description" in st.session_state and st.session_state["job_description"]==None)):
            if job_required or "job_required" in st.session_state:
                st.session_state.job_posting_checkmark=":red[(required)]"
            else:
                st.session_state.job_posting_checkmark="(optional)"
        if job_required or "job_required" in st.session_state:
            st.session_state.expanded=True
        else:
            st.session_state.expanded=False

        if "job_required" in st.session_state:
            st.info("AI will tailor your resume to a job posting. Please provide either a link or complete job description")
        elif ("job_posting_path" not in st.session_state and "job_description" not in st.session_state or ("job_description" in st.session_state and st.session_state["job_description"]==None)):
            st.info("AI will evaluate your resume only. If you want your resume tailored also, please provide a job posting")
        else:
            st.info("Your resume will be evaluated and tailored to the job posting")
        skip_evaluation = st.checkbox("skip evaluation", key="skip_evaluation", on_change=self.form_callback)
        with st.expander(f"Add a job posting for tailoring {st.session_state.job_posting_checkmark}", expanded=st.session_state.expanded):
            job_posting = st.radio(f" ", 
                                key="job_posting_radio", options=["job description", "job posting link"], 
                                index = 1 if "job_description"  not in st.session_state else 0
                                )
            if job_posting=="job posting link":
                job_posting_link = st.text_input(label="Job posting link",
                                                key="job_posting", 
                                                on_change=self.form_callback,
                                                    # disabled=st.session_state.job_posting_disabled
                                                    )
            elif job_posting=="job description":
                job_description = st.text_area("Job description", 
                                            key="job_descriptionx", 
                                            value=st.session_state.job_description if "job_description" in st.session_state else "",
                                                on_change=self.form_callback, 
                                                #  disabled=st.session_state.job_description_disabled
                                                )
        c1, separator, c2=st.columns([5, 1, 3])
        with c1:
            resume= st.file_uploader(label=f"Upload your most recent resume {st.session_state.resume_checkmark}", 
                                    key="resume",
                                    type=["pdf","odt", "docx","txt"], 
                                    on_change=self.form_callback,
                                    # disabled=st.session_state.resume_disabled,
                                    )
            if resume: 
                self.process([resume],"resume" )
        with separator:
            add_vertical_space(5)
            st.write("or")
        with c2:
            add_vertical_space(5)
            if self.userId:
                if st.session_state["user_profile_dict"]:
                    st.checkbox("use my default resume", key="default_resume_checkbox", on_change=self.form_callback)
                else:
                    st.session_state["redirect_page"]="home.py"
                    st.session_state["user_mode"] = "display_profile"
                    st.page_link("pages/user.py", label="create my default resume", )       
            else:
                st.write("Login to use or create a default resume")
                if st.button("login", type="primary"):
                    st.session_state["redirect_page"]="home.py"
                    st.switch_page("pages/user.py")
        if st.button(label="next",
                           key="next_button", 
                           disabled=st.session_state.conti_disabled, 
                          ):
            st.session_state["resume help"]=True
            st.rerun()


    # def skip_evaluation_callback(self, ):

    #     if st.session_state["skip_evaluation"]:
    #         st.session_state["job_required"]=True
    #     else:
    #         if "job_required" in st.session_state:
    #             del st.session_state["job_required"]


    # @st.fragment
    def process_selection(self, ):

        # Generate resume and job posting dictionaries
        posting_q=None
        resume_q=None
        if "default_resume_checkbox" in st.session_state and st.session_state["default_resume_checkbox"]:
            st.session_state["resume_path_final"] = st.session_state["user_profile_dict"]["resume_path"]
        else:
            st.session_state["resume_path_final"]=st.session_state["resume_path"]
        if "skip_evaluation" not in st.session_state or st.session_state["skip_evaluation"]==False:
            st.session_state["evaluation"]=True
        resume_q = queue.Queue()
        resume_t= threading.Thread(target=retrieve_or_create_resume_info, 
                                args=(st.session_state.resume_path_final, resume_q, ),
                                daemon=True)
        resume_t.start()
        if ("job_posting_path" in st.session_state and st.session_state.job_posting_radio=="job posting link") or  ("job_description" in st.session_state and st.session_state.job_posting_radio=="job description"):
            st.session_state["tailoring"]=True
            posting_q = queue.Queue()
            posting_t=threading.Thread(
                target = retrieve_or_create_job_posting_info, 
                args = (
                st.session_state.job_posting_path if "job_posting_path" in st.session_state and st.session_state.job_posting_radio=="job posting link" else "",
                 st.session_state.job_description if "job_description" in st.session_state and st.session_state.job_posting_radio=="job description" else "",  
                 posting_q),
                 daemon=True,
            )
            posting_t.start()
        if resume_q:
            resume_t.join()
            st.session_state["resume_dict"]=resume_q.get()
        if posting_q:
            posting_t.join()
            st.session_state["job_posting_dict"] = posting_q.get()

                

    


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
        
    # def retrieve_downloads(self):

    #     """ Displays AI generated files in sidebar downloads tab, if available, of the current session. """
        
    #     # files = self.check_user_downloads(st.session_state["current_session"])
    #     files = self.check_user_downloads()
    #     with st.session_state.download_placeholder.container():
    #         if files:
    #             for file in files:
    #                 st.markdown(self.binary_file_downloader_html(file), unsafe_allow_html=True)
    #         else:
    #             st.write("AI generated files will be shown here")

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
        # try:
        #     selected=st.session_state.type_selectionx
        #     if selected:
        #         # st.session_state.cl_type_checkmark="✅"
        #         st.session_state["type_selection"]=selected
        # except Exception:
        #     pass
        try:
            resume=st.session_state.resume
            if resume:
                self.process([resume],"resume" )
        except Exception:
            pass
        try:
            job_posting=st.session_state.job_posting
            if job_posting:
                # st.session_state.job_posting=""
                self.process(job_posting, "job_posting")
        except Exception:
            pass
        try:
            job_description=st.session_state.job_descriptionx
            if job_description:
               self.process(job_description, "job_description")
        except Exception:
            pass
        try: 
            skip_eval = st.session_state["skip_evaluation"]
            if skip_eval:
                st.session_state["job_required"]=True
            else:
                if "job_required" in st.session_state:
                    del st.session_state["job_required"]
        except Exception:
            pass
        # try:
        #     use_default = st.session_state["default_resume_checkbox"]
        #     if use_default:
        #         st.session_state["use_default_resume"]=True 
        # except Exception:
        #     pass

        # try:
        #     pursuit_job=st.session_state.pursuit_job
        #     if pursuit_job:
        #         st.session_state.pursuit_job=""
        #         self.process_uploads(job_posting, "job_posting")
        # except Exception:
        #     pass
        # try:
        #     # files = st.session_state.files 
        #     file_key = f"files_{str(st.session_state.file_counter)}"
        #     files = st.session_state[file_key]
        #     if files:
        #         self.process_uploads(files, "files")
        #         st.session_state["file_counter"] += 1
        #         # st.session_state.files=""
        # except Exception:
        #     pass
        # try:
        #     links = st.session_state.links
        #     if links:
        #         self.process_uploads(links, "links")
        #         st.session_state.links=""
        # except Exception:
        #     pass
        # try:
        #     about_job = st.session_state.aboutJob
        #     if about_job:
        #         self.new_chat.update_entities(f"about_job:{about_job} /n"+"~~~~", '~~~~')
        #         st.session_state.aboutJob=""
        #         st.toast("successfully submitted")
        # except Exception:
        #     pass

        ## Passes the previous user question to the agent one more time after user uploads form
        # try:
        #     # print(f"QUESTION INPUT: {st.session_state.questionInput}")
        #     if st.session_state.questionInput!="":
        #         st.session_state.input = st.session_state.questionInput
        #         self.question_callback(self.callback_done, append_question=False)
        # # 'Chat' object has no attribute 'question': exception occurs when user has not asked a question, in this case, pass
        # except AttributeError:    
        #    pass






        
    



    def process(self, uploads: Any, upload_type: str) -> None:

        """Processes user uploads including converting all format to txt, checking content safety, content type, and content topics. 

        Args:
            
            uploads: files or links saved when user uploads on Streamlit
            
            upload_type: "files" or "links"
    
        """

        if upload_type=="resume":
            result = process_uploads(uploads, st.session_state.save_path, st.session_state.sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="resume":
                    st.session_state["resume_path"]= end_path
                    st.session_state.resume_checkmark="✅"
                    # st.session_state["resume_dict"] = retrieve_or_create_resume_info(resume_path=end_path, )
                else:
                    # st.session_state.resume_checkmark=":red[*]"
                    st.info("Please upload your resume here")
            else:
                st.info("Please upload your resume here")
        elif upload_type=="job_posting":
            result = process_links(uploads, st.session_state.save_path, st.session_state.sessionId)
            if result is not None:
                content_safe, content_type, content_topics, end_path = result
                if content_safe and content_type=="job posting":
                    st.session_state["job_posting_path"]=end_path
                    st.session_state.job_posting_checkmark="✅"
                else:
                    # st.session_state.job_posting_checkmark=":red[*]"
                    st.info("Please upload your job posting link here")
            else:
                st.info("That didn't work. Please try pasting the content in job description instead.")
        elif upload_type=="job_description":
            result = process_inputs(uploads, match_topic="job posting or job description")
            if result is not None:
                st.session_state.job_posting_checkmark="✅"
                st.session_state["job_description"] = uploads  
            else:
                st.info("Please share a job description here")

        


    # def update_entities(self, content_type:str, content_topics: set[str], end_path:str) -> None:

    #     """ Adds entities to chat agent. 
        
    #     Args:

    #         content_type: file's content categorized as one of the following ["empty", "resume", "cover letter", "job posting", "education program", "personal statement", "browser error", "learning material", "other"]

    #         content_topics: topics of the content, if available, for learning material specifically
            
    #         end_path: file path
            
    #     """

    #     if content_type!="other" and content_type!="learning material":
    #         delimiter=""
    #         if content_type=="job posting":
    #             delimiter = "@@@"
    #         elif content_type=="resume":
    #             delimiter = "$$$"    
    #         if content_type=="job posting":
    #             content = read_txt(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name,s3=st.session_state.s3_client)
    #             token_count = num_tokens_from_text(content)
    #             if token_count>max_token_count:
    #                 shorten_content(end_path, content_type) 
    #         content_type = content_type.replace(" ", "_").strip()
    #         entity = f"""{content_type}_file: {end_path} /n"""+delimiter
    #         self.new_chat.update_entities(entity, delimiter)
    #     if content_type=="learning material" :
    #         # update user material, to be used for "search_user_material" tool
    #         delimiter = "###"
    #         record_name = self.userId if self.userId is not None else st.session_state.sessionId
    #         vs_path = user_vs_name if st.session_state.storage=="CLOUD" else os.path.join(st.session_state.save_path, st.session_state.sessionId, user_vs_name)
    #         update_vectorstore(end_path=end_path, vs_path =vs_path,  index_name=user_vs_name, record_name=record_name, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
    #         entity = f"""user_material_path: {vs_path} /n"""+delimiter
    #         self.new_chat.update_entities(entity, delimiter)
    #         if content_topics:
    #             delimiter = "###"
    #             topics = ", ".join(content_topics)
    #             entity = f"""user_material_topics: {topics} /n"""+delimiter
    #             self.new_chat.update_entities(entity, delimiter)



    
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



    # # @st.cache_resource()
    # def check_user_downloads(self) -> List[str]:

    #     """ Checks AI generated files in download folder and returns a list of file paths. """

    #     download_dir = os.path.join(st.session_state.save_path, st.session_state.sessionId, "downloads")
    #     generated_files = []
    #     if st.session_state.storage=="LOCAL":
    #         try:
    #             for path in Path(download_dir).glob('**/*.docx*'):
    #                 file=str(path)
    #                 print(f"DOWNLOAD FILE: {file}")
    #                 generated_files.append(file)
    #         except Exception:
    #             pass
    #     elif st.session_state.storage=="CLOUD":
    #         try:
    #             response = st.session_state.s3_client.list_objects(Bucket=st.session_state.bucket_name, Prefix=download_dir)
    #             for content in response.get('Contents', []):
    #                 file=content.get['Key']
    #                 if Path(file).suffix==".docx":
    #                     generated_files.append(file)
    #         except Exception:
    #             pass
    #     return generated_files

    
# class StreamHandler(BaseCallbackHandler):
#     def __init__(self, container, initial_text=""):
#         self.container = container
#         self.text = initial_text

#     def on_llm_new_token(self, token: str, **kwargs) -> None:
#         self.text += token
#         # self.container.markdown(self.text)
#         with self.container.container():
#             st.chat_message("ai").write(self.text)


if __name__ == '__main__':

    advisor = Main()

