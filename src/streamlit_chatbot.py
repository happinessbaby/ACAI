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
from langchain.callbacks import StreamlitCallbackHandler
from backend.career_advisor import ChatController
from backend.mock_interview import InterviewController
from callbacks.capturing_callback_handler import playback_callbacks
from utils.basic_utils import convert_to_txt, read_txt, retrieve_web_content, html_to_text
from utils.openai_api import get_completion, num_tokens_from_text, check_content_safety
from dotenv import load_dotenv, find_dotenv
from utils.common_utils import  check_content, evaluate_content, generate_tip_of_the_day, shorten_content
import asyncio
import concurrent.futures
import subprocess
import sys
import re
from json import JSONDecodeError
from multiprocessing import Process, Queue, Value
import pickle
import requests
from functools import lru_cache
from typing import Any
import multiprocessing as mp
from utils.langchain_utils import merge_faiss_vectorstore, create_tag_chain
import openai
import json
from st_pages import show_pages_from_config, add_page_title, show_pages, Page
from st_clickable_images import clickable_images
from st_click_detector import click_detector
from streamlit_modal import Modal
import base64
from langchain.tools import tool
import streamlit.components.v1 as components, html
from PIL import Image
from my_component import my_component
# from thread_safe_st import ThreadSafeSt
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import threading
_ = load_dotenv(find_dotenv()) # read local .env file


# Either this or add_indentation() MUST be called on each page in your
# app to add indendation in the sidebar

# Optional -- adds the title and icon to the current page
# add_page_title()

# Specify what pages should be shown in the sidebar, and what their titles and icons
# should be
show_pages(
    [
        Page("streamlit_chatbot.py", "Home", "🏠"),
        Page("streamlit_interviewbot.py", "Mock Interview", ":books:"),
        # Page("Streamlit_journey.py", "My Journey"),
        # Page("streamlit_resources.py", "Resources", ":busts_in_silhouette:" ),
    ]
)


# st.title("Testing Streamlit custom components")
# my_compnonent()
openai.api_key = os.environ['OPENAI_API_KEY']
save_path = os.environ["SAVE_PATH"]
temp_path = os.environ["TEMP_PATH"]
template_path = os.environ["TEMPLATE_PATH"]
placeholder = st.empty()
max_token_count=3500
topic = "jobs"


class Chat():

    # userid: str=""
    ctx = get_script_run_ctx()

    def __init__(self):
        self._create_chatbot()

  
    def _create_chatbot(self):

        textinput_styl = f"""
        <style>
            .stTextInput {{
            position: fixed;
            bottom: 3rem;
            }}
        </style>
        """
        selectbox_styl = f"""
        <style>
            .stSelectbox {{
            position: fixed;
            bottom: 3rem;
            }}
        </style>
        """

        st.markdown(textinput_styl, unsafe_allow_html=True)
        st.markdown(selectbox_styl, unsafe_allow_html=True)

        with placeholder.container():

            if "userid" not in st.session_state:
                st.session_state["userid"] = str(uuid.uuid4())
                print(f"Session: {st.session_state.userid}")
                self.userid = st.session_state.userid
                # super().__init__(st.session_state.userid)
            if "basechat" not in st.session_state:
                new_chat = ChatController(st.session_state.userid)
                st.session_state["basechat"] = new_chat 
            # if "tipofday" not in st.session_state:
            #     tip = generate_tip_of_the_day(topic)
            #     st.session_state["tipofday"] = tip
            #     st.write(tip)
                
            try:
                self.new_chat = st.session_state.basechat
            except AttributeError as e:
                raise e
        
            try: 
                temp_dir = os.path.join(temp_path, st.session_state.userid)
                os.mkdir(temp_dir)
                user_dir = os.path.join(save_path, st.session_state.userid)
                os.mkdir(user_dir)
                download_dir = os.path.join(user_dir, "downloads")
                os.mkdir(download_dir)
                # if "download_dir" not in st.session_state:
                #     st.session_state["download_dir"] = download_dir
            except FileExistsError:
                pass

            # Initialize chat history
            # if "messages" not in st.session_state:
            #     st.session_state.messages = []


            # expand_new_thoughts = st.sidebar.checkbox(
            #     "Expand New Thoughts",
            #     value=True,
            #     help="True if LLM thoughts should be expanded by default",
            # )
            SAMPLE_QUESTIONS = {
                "":"",
                # "upload my files": "upload",
                "help me generate a cover letter": "generate",
                "Evaluate my resume": "evaluate",
                "rewrite my resume using a new template": "reformat",
            }

            ## questions stores User's questions
            if 'questions' not in st.session_state:
                st.session_state['questions'] = list()
            ## responses stores AI generated responses
            if 'responses' not in st.session_state:
                st.session_state['responses'] = list()
            # hack to clear text after user input
            if 'questionInput' not in st.session_state:
                st.session_state["questionInput"] = ''      
            if 'spinner_placeholder' not in st.session_state:
                st.session_state["spinner_placeholder"] = st.empty()
            ## hacky way to clear uploaded files once submitted
            if "counter" not in st.session_state:
                st.session_state["counter"] = 0
            # if "generated_files" not in st.session_state:
            #     st.session_state["generated_files"] = list()
            # Sidebar section
            with st.sidebar:
                st.title("""Hi, I'm Acai, a career AI.""")
                add_vertical_space(1)
                st.markdown('''
                                                    
                Chat with me, Upload & Share, or click on the Mock Interview tab above to try it out! 
                                                    
                ''')

                # st.button("Upload my files", key="upload_file_button", on_click=self.file_upload_popup)
                # st.button("Share a link", key="link_button", on_click=self.link_share_popup)
                with st.expander("Upload & Share"):
                    st.file_uploader(label="Files",
                                    accept_multiple_files=True,
                                    # key="files",
                                    key= f"files_{str(st.session_state.counter)}",
                                    on_change=self.form_callback)
                    st.text_area(label="Links", 
                            placeholder="This can be a job posting url for example", 
                            key = "links", 
                            # label_visibility="hidden",
                            # help="This can be a job posting, for example.",
                            on_change=self.form_callback)
                    st.text_area(label="About",
                                 key="about_me",
                                 placeholder="Tell me about your job application or career goals",
                                 on_change=self.form_callback)
                    
                # file_path = "/home/tebblespc/GPT-Projects/ACAI/ACAI/src/my_material/analyst1.txt"    
                with st.expander("Download your files"):
                    files = self.check_user_downloads()
                    # files = st.session_state.generated_files
                    if files:
                        for file in files:
                            st.markdown(self.binary_file_downloader_html(file), unsafe_allow_html=True)
                    else:
                        st.write("AI generated files will be shown here")

                st.markdown('''
                                                    
                Note: 
                    
                Only the most recent uploaded files and links will be used.
                            
                If you refresh the page, your session conversation and downloads will be lost.
                                                    
                ''')
            

            
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
                

                add_vertical_space(3)
            # Chat section
            ## Displays the current conversation
            if st.session_state['responses']:
                for i in range(len(st.session_state['responses'])):
                    try:
                        message(st.session_state['questions'][i], is_user=True, key=str(i) + '_user',  avatar_style="initials", seed="Yueqi", allow_html=True)
                        message(st.session_state['responses'][i], key=str(i), avatar_style="initials", seed="AI", allow_html=True)
                    except Exception:
                        pass   

            self.callback_done = threading.Event()
            thread = threading.Thread(target=self.question_callback, args=(self.callback_done, ))
            add_script_run_ctx(thread, self.ctx)
            thread.start()

            c1, c2 = st.columns([2, 1])
            # User chat input area
            c1.text_input("Chat with me: ",
                        # value=st.session_state.prefilled, 
                        key="input", 
                        label_visibility="hidden", 
                        placeholder="Chat with me",
                        on_change = self.question_callback, 
                        args = [self.callback_done],
                        )
            # Select from sample questions
            c2.selectbox(label="Sample questions",
                        options=sorted(SAMPLE_QUESTIONS.keys()), 
                        key = "prefilled",
                        format_func=lambda x: '-----sample questions-----' if x == '' else x,
                        label_visibility= "hidden",
                        on_change = self.question_callback, 
                        args = [self.callback_done],
                        )

            # st.text_input("Chat with me: ", "", key="input", on_change = self.question_callback)



    def question_callback(self, callback_done, append_question=True):

        """ Sends user input to chat agent. """

        question = None
        try:
            if st.session_state.input!="" or st.session_state.prefilled!="":
                callback_done.set() 
                question = st.session_state.input if st.session_state.input else st.session_state.prefilled      
        except Exception:
            pass
        callback_done.wait()
        if question is not None:
            response = None
            with st.session_state.spinner_placeholder, st.spinner("Please wait..."):
                response = self.new_chat.askAI(st.session_state.userid, question, callbacks = None)
            # response="functional"
            if response == "functional" or response == "chronological" or response == "student":
                self.resume_template_popup(response)
            elif response:
                if append_question:
                    st.session_state.questions.append(question)
                st.session_state.responses.append(response)
            st.session_state.questionInput =  st.session_state.input if st.session_state.input else st.session_state.prefilled  
            st.session_state.input = ''    
            st.session_state.prefilled = ''
    


    def file_upload_popup(self, callback_msg=""):

        """Popup for user to upload files. """

        # modal = Modal(title="Upload your files", key="file_popup", max_width=600)
        placeholder = st.empty()
        if "file_modal" not in st.session_state:
            st.session_state["file_modal"] =  Modal(title="    ", key="file_popup", max_width=600)
        with placeholder.container():
            with st.session_state.file_modal.container():
                st.write(callback_msg)
                if "file_loading" not in st.session_state:
                    st.session_state["file_loading"]=st.empty()
                col1, _ = st.columns([10, 1])
                with col1:
                    with st.form(key='file_popup_form', clear_on_submit=True):
                        # add_vertical_space(1)
                        st.file_uploader(
                            label="Upload your resume, cover letter, or anything you want to share with me.",
                            type=["pdf","odt", "docx","txt", "zip", "pptx"], 
                            key = "files",
                            # help = "This can be your resume, cover letter, or anything else you want to share with me. ",
                            label_visibility="hidden",
                            accept_multiple_files=True
                            )
                        # add_vertical_space(1)
                        st.form_submit_button(label='Submit', on_click=self.form_callback)  


    def link_share_popup(self, callback_msg=""):

        """Popup for user to share url. """
    
        # modal = Modal(title="Share a link", key="link_popup", max_width=500)
        placeholder=st.empty()
        if "link_modal" not in st.session_state:
            st.session_state["link_modal"] =  Modal(title="   ", key="link_popup", max_width=500)
        with placeholder.container():
            with st.session_state.link_modal.container():
                st.write(callback_msg)
                if "link_loading" not in st.session_state:
                    st.session_state["link_loading"]=st.empty()
                col1, _ = st.columns([10, 1])
                with col1:
                    with st.form(key="link_popup_form", clear_on_submit=True):
                        st.text_area(
                            label="", 
                            placeholder="This can be a job posting url for example", 
                            key = "links", 
                            # label_visibility="hidden",
                            help="If the link does not work, try saving the content and upload it as a file.",
                            )
                        st.form_submit_button(label="Submit", on_click=self.form_callback)



 
    def form_callback(self):

        """ Processes form information after form submission. """
   
        try:
            # files = st.session_state.files 
            file_key = f"files_{str(st.session_state.counter)}"
            files = st.session_state[file_key]
            if files:
                self.process_file(files)
                st.session_state["counter"] += 1
                # st.session_state.files=""
        except Exception:
            pass
        try:
            links = st.session_state.links
            if links:
                self.process_link(links)
                st.session_state.links=""
        except Exception:
            pass
        # try:
        #     job = st.session_state.job
        #     if job:
        #         st.toast("sucessfully submitted")
        #         self.new_chat.update_entities(f"job:{job} /n ###")
        #         st.session_state.job=""
        # except Exception:
        #     pass
        # try:
        #     company = st.session_state.company
        #     if company:
        #         st.toast("sucessfully submitted")
        #         self.new_chat.update_entities(f"company:{company} /n ###")
        #         st.session_state.company=""
        # except Exception:
        #     pass
        try:
            about_me = st.session_state.about_me
            self.new_chat.update_entities(f"about me:{about_me} /n ###")
            st.toast("successfully submitted")
            # self.process_about_me(about_me)
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


    @st.cache_data(experimental_allow_widgets=True)
    def resume_template_popup(_self, resume_type:str):

        """ Popup window for user to select a resume template based on the resume type. """

        print("TEMPLATE POPUP")
        placeholder = st.empty()
        modal = Modal(key="template_popup", title=f"Pick a template", max_width=1000)
        with placeholder.container():
            with modal.container():
                col1, _ = st.columns([10, 1])
                with col1:
                    with st.form( key='template_form', clear_on_submit=True):
                        template_idx = my_component(resume_type, "templates")
                        # st.markdown(img)
                        st.form_submit_button(label='Submit', on_click=_self.resume_template_callback, args=[resume_type, template_idx])



    def resume_template_callback(self, resume_type:str, template_idx:str):

        """ Calls the resume_rewriter tool to rewrite the resume according to the chosen resume template. """

        # if st.session_state.templates:
        #     template_idx = st.session_state.templates
        #     print(f"MY COMPONENT KEY: {template_idx}")
        print(f"TEMPLATE IDX:{template_idx}")
        resume_template_file = os.path.join(template_path,resume_type, f"{resume_type}{template_idx}.docx")
        question = f"""Please help user rewrite their resume using the resume_rewriter tool with the following resume_template_file:{resume_template_file}. """
        # response = self.new_chat.askAI(st.session_state.userid, question, callbacks=None)
        # st.session_state.questions.append(st.session_state.questionInput)
        # st.session_state.responses.append(response) 
        st.session_state.input = question  
        self.question_callback(self.callback_done, append_question=False)


    # def set_clickable_icons(self, dir_path):

    #     """ Displays a set of clickable images from a directory of resume template images. """

    #     images = []
    #     for path in Path(dir_path).glob('**/*.png'):
    #         file = str(path)
    #         with open(file, "rb") as image:
    #             encoded = base64.b64encode(image.read()).decode()
    #             images.append(f"data:image/png;base64,{encoded}")
    #     clicked = clickable_images(
    #         images,
    #         titles=[f"Image #{str(i)}" for i in range(2)],
    #         div_style={"display": "flex", "justify-content": "center", "flex-wrap": "wrap"},
    #         img_style={"margin": "5px", "height": "200px"},
    #     )
        # if clicked>-1:
        #     change_template = False
        #     if "last_clicked" not in st.session_state:
        #         st.session_state["last_clicked"] = clicked
        #         change_template = True
        #     else:
        #         if clicked != st.session_state["last_clicked"]:
        #             st.session_state["last_clicked"] = clicked
        #             change_template = True
        #     if change_template:
        #         print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")
        #         st.session_state["resume_template"] = f"resume_template: {dir_path}functional-{clicked}.png"


        


                
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
                    "enum": ["personal life description", "job or program description", "company or institution description", "resume help"],
                    "description": "determines if the statement contains certain topic",
                },
            },
            # "required": ["topic", "sentiment", "aggressiveness"],
            "required": ["topic"],
        }
        response = create_tag_chain(tag_schema, user_input)
        topic = response.get("topic", "")
        # if topic == "upload files":
        #     self.file_upload_popup()
        # else: 
        if topic == "personal life description" or topic=="job or program description" or topic=="company or institution description":
            self.new_chat.update_entities(f"about me:{user_input} /n ###")
        return user_input
    




    # def process_about_me(self, about_me: str) -> None:
    
        """ Processes user's about me input for content type and processes any links in the description. """

        # content_type = """a job or study related user request. """
        # user_request = evaluate_content(about_me, content_type)
        # # about_me_summary = get_completion(f"""Summarize the following about me, if provided, and ignore all the links: {about_me}. """)
        # self.new_chat.update_entities(f"about me:{about_me_summary} /n ###")
        # if user_request:
        #     self.question = about_me
        # process any links in the about me
        # urls = re.findall(r'(https?://\S+)', about_me)
        # print(urls)
        # if urls:
        #     for url in urls:
        #         self.process_link(url)




    def process_file(self, uploaded_files: Any) -> None:

        """ Processes user uploaded files including converting all format to txt, checking content safety, and categorizing content type  """
        # with st.session_state.file_loading, st.spinner("Processing..."):
        with st.session_state.spinner_placeholder, st.spinner("Processing..."):
            for uploaded_file in uploaded_files:
                file_ext = Path(uploaded_file.name).suffix
                filename = str(uuid.uuid4())+file_ext
                tmp_save_path = os.path.join(temp_path, st.session_state.userid, filename)
                with open(tmp_save_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                end_path =  os.path.join(save_path, st.session_state.userid, Path(filename).stem+'.txt')
                # Convert file to txt and save it to uploads
                convert_to_txt(tmp_save_path, end_path)
                # content_safe, content_type, content_topics = check_content(end_path)
                # print(content_type, content_safe, content_topics) 
                content_safe, content_type = check_content(end_path)
                print(content_type, content_safe) 
                if content_safe and content_type!="empty":
                    self.update_entities(content_type, end_path)
                    st.toast("sucessfully submitted")
                else:
                    os.remove(end_path)
                    st.toast(f"Failed processing {Path(uploaded_file.name).root}. Please try another file!")
                    # self.file_upload_popup(callback_msg=f"Failed processing {Path(uploaded_file.name).root}. Please try another file!")
        
        

    def process_link(self, links: Any) -> None:

        """ Processes user shared links including converting all format to txt, checking content safety, and categorizing content type """
        # with st.session_state.link_loading, st.spinner("Processing..."):
        with st.session_state.spinner_placeholder, st.spinner("Processing..."):
            end_path = os.path.join(save_path, st.session_state.userid, str(uuid.uuid4())+".txt")
            links = re.findall(r'(https?://\S+)', links)
            if html_to_text(links, save_path=end_path):
            # if (retrieve_web_content(posting, save_path = end_path)):
                # content_safe, content_type, content_topics = check_content(end_path)
                # print(content_type, content_safe, content_topics) 
                content_safe, content_type = check_content(end_path)
                print(content_type, content_safe) 
                if (content_safe and content_type!="empty" and content_type!="browser error"):
                    self.update_entities(content_type, end_path)
                    st.toast("sucessfully submitted")
                else:
                    os.remove(end_path)
                    st.toast(f"Failed processing {str(links)}. Please try another link!")
                    # self.link_share_popup(callback_msg=f"Failed processing {str(links)}. Please try another link!")
            else:
                os.remove(end_path)
                st.toast(f"Failed processing {str(links)}. Please try another link!")
                # self.link_share_popup(callback_msg=f"Failed processing {str(links)}. Please try another link!")



    def update_entities(self, content_type:str, end_path:str) -> str:

        """ Update entities for chat agent. """

        if content_type!="other" and content_type!="learning material":
            if content_type=="job posting":
                content = read_txt(end_path)
                token_count = num_tokens_from_text(content)
                if token_count>max_token_count:
                    shorten_content(end_path, content_type) 
            content_type = content_type.replace(" ", "_").strip()        
            entity = f"""{content_type}_file: {end_path} /n ###"""
            self.new_chat.update_entities(entity)
        if content_type=="learning material" :
            # update user material, to be used for "search_user_material" tool
            self.update_vectorstore(end_path)


    def update_vectorstore(self, end_path: str) -> None:

        """ Update vector store for chat agent. """

        # entity = f"""topics: {str(content_topics)} """
        self.new_chat.update_entities(entity)
        vs_name = "user_material"
        vs = merge_faiss_vectorstore(vs_name, end_path)
        vs_path =  os.path.join(save_path, st.session_state.userid, vs_name)
        vs.save_local(vs_path)
        entity = f"""user_material_path: {vs_path} /n ###"""
        self.new_chat.update_entities(entity)


    def binary_file_downloader_html(self, file: str):

        """ Gets the download link for generated file. """

        with open(file, 'rb') as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(file)}">Download the cover letter</a>'
        return href
    
    def check_user_downloads(self):

        """ Check generated files in download folder and returns a list of file names. """

        download_dir = os.path.join(save_path, st.session_state.userid, "downloads")
        generated_files = []
        if os.listdir(download_dir):
            print("Some files found in the directory.")
            for path in Path(download_dir).glob('**/*.*'):
                file=str(path)
                generated_files.append(file)
                # st.session_state.generated_files.append(file)
        return generated_files

    




if __name__ == '__main__':

    advisor = Chat()
    # asyncio.run(advisor.initialize())
