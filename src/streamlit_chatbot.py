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
my_component("World")


class Chat():

    userid: str=""

    def __init__(self):
        self._create_chatbot()

  
    def _create_chatbot(self):

        styl = f"""
        <style>
            .stTextInput {{
            position: fixed;
            bottom: 3rem;
            }}
        </style>
        """
        styl1 = f"""
        <style>
            .stSelectbox {{
            position: fixed;
            bottom: 3rem;
            }}
        </style>
        """
        # styl = f"""
        # <style>
        #     .element-container:nth-of-type(1) stTextInput {{
        #     position: fixed;
        #     bottom: 3rem;
        #     }}
        # </style>
        # """
        st.markdown(styl, unsafe_allow_html=True)
        st.markdown(styl1, unsafe_allow_html=True)

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
                temp_dir = temp_path+st.session_state.userid
                user_dir = save_path+st.session_state.userid
                os.mkdir(temp_dir)
                os.mkdir(user_dir)
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
                "help me write a cover letter": "generate",
                "can you evaluate my resume?": "evaluate",
                "rewrite my resume using a new template": "reformat",
            }

            # Generate empty lists for generated and past.
            ## past stores User's questions
            if 'questions' not in st.session_state:
                st.session_state['questions'] = list()
            ## generated stores AI generated responses
            if 'responses' not in st.session_state:
                st.session_state['responses'] = list()

            # hack to clear text after user input
            if 'questionInput' not in st.session_state:
                st.session_state.questionInput = ''

            #Sidebar section
            with st.sidebar:
                st.title("""Hi, I'm your career AI advisor Acai!""")
                add_vertical_space(1)
                st.markdown('''
                                                    
                Chat with me, upload and share whatever you want, or click on the Mock Interview tab above to try it out! 
                                                    
                ''')

                st.button("Upload my file", key="upload_file", on_click=self.file_upload_popup)
                st.text_area(label="Share a link", 
                        placeholder="This can be a job posting url for example", 
                        key = "link", 
                        # label_visibility="hidden",
                        # help="This can be a job posting, for example.",
                        on_change=self.form_callback)
            

                # st.markdown("Quick navigation")
                # with st.form( key='my_form', clear_on_submit=True):

                #     # col1, col2= st.columns([5, 5])

                #     # with col1:
                #     #     job = st.text_input(
                #     #         "job/program",
                #     #         "",
                #     #         key="job",
                #     #     )
                    
                #     # with col2:
                #     #     company = st.text_input(
                #     #         "company/institution",
                #     #         "",
                #     #         key = "company"
                #     #     )

                #     # about_me = st.text_area(label="About", placeholder="""You can say,  I want to apply for the MBA program at ABC University, or I wish to work for XYZ as a customer service representative. 
                    
                #     # If you want to provide any links, such as a link to a job posting, please paste it here. """, key="about_me")

                #     uploaded_files = st.file_uploader(label="Upload your files",
                #                                       help = "This can be your resume, cover letter, or anything else you want to share with me. ",
                #                                     type=["pdf","odt", "docx","txt", "zip", "pptx"], 
                #                                     key = "files",
                #                                     accept_multiple_files=True)

                    
                #     link = st.text_area(label="Share your link", 
                #                         placeholder="Paste a link here; this can be a job posting url, for example.", 
                #                         key = "link", 
                #                         label_visibility="hidden",
                #                         help="This can be a job posting url, for example.",)

                #     add_vertical_space(1)
                #     # prefilled = st.selectbox(label="Sample questions",
                #     #                         options=sorted(SAMPLE_QUESTIONS.keys()), 
                #     #                         key = "prefilled",
                #     #                         format_func=lambda x: '' if x == '' else x,
                #     #                         )


                #     submit_button = st.form_submit_button(label='Submit', on_click=self.form_callback)

                add_vertical_space(3)
            # Chat section
            if st.session_state['responses']:
                for i in range(len(st.session_state['responses'])-1, -1, -1):
                    message(st.session_state['responses'][i], key=str(i), avatar_style="initials", seed="ACAI", allow_html=True)
                    message(st.session_state['questions'][i], is_user=True, key=str(i) + '_user',  avatar_style="initials", seed="Yueqi", allow_html=True)

            c1, c2 = st.columns([2, 1])


            # if "prefilled" not in st.session_state:
            #     st.session_state["prefilled"] = ""
            c1.text_input("Chat with me: ",
                        # value=st.session_state.prefilled, 
                        key="input", 
                        label_visibility="hidden", 
                        placeholder="Chat with me",
                        on_change = self.question_callback,
                        )
            # Automatically select the last input with last_index
            c2.selectbox(label="Sample questions",
                        options=sorted(SAMPLE_QUESTIONS.keys()), 
                        key = "prefilled",
                        format_func=lambda x: '---sample questions---' if x == '' else x,
                        label_visibility= "hidden",
                        on_change = self.question_callback,
                        )

            # st.text_input("Chat with me: ", "", key="input", on_change = self.question_callback)


    def question_callback(self):

        """ Sends user input to chat agent. """
        if st.session_state.input!="":
            self.question = self.process_user_input(st.session_state.input) 
        elif st.session_state.prefilled!="":
            self.question = self.process_user_input(st.session_state.prefilled)
        if self.question:
            response = self.new_chat.askAI(st.session_state.userid, self.question, callbacks = None)
            self.resume_template_popup(response)

            # if response == "functional" or response == "chronological" or response == "student":
            #     self.resume_template_popup(response)
            # else:
            #     st.session_state.questions.append(self.question)
            #     st.session_state.responses.append(response)
        st.session_state.questionInput = st.session_state.input
        st.session_state.input = ''    

    
    def file_upload_popup(self):

        """Use this tool when user wants to upload their files."""

        modal = Modal(title="Upload your files", key="popup")
        with modal.container():
            with st.form( key='my_form', clear_on_submit=True):
                # add_vertical_space(1)
                st.file_uploader(label="Upload your resume, cover letter, or anything you want to share with me.",
                                type=["pdf","odt", "docx","txt", "zip", "pptx"], 
                                key = "files",
                                # help = "This can be your resume, cover letter, or anything else you want to share with me. ",
                                label_visibility="hidden",
                                accept_multiple_files=True)
                # add_vertical_space(1)
                st.form_submit_button(label='Submit', on_click=self.form_callback)  
 
    def form_callback(self):

        """ Processes form information after form submission. """

        try:
            files = st.session_state.files 
            self.process_file(files)
        except Exception:
            pass
        try:
            link = st.session_state.link
            self.process_link(link)
        except Exception:
            pass
        # try:
        #     about_me = st.session_state.about_me
        #     self.process_about_me(about_me)
        # except Exception:
        #     pass
        # if st.session_state.prefilled:
        #     st.session_state.input = st.session_state.prefilled
        #     self.question_callback()
        # else:
        # passes the previous user question to the agent one more time after user uploads form
        try:
            print(f"QUESTION INPUT: {st.session_state.questionInput}")
            if st.session_state.questionInput!="":
                st.session_state.input = st.session_state.questionInput
                self.question_callback()
                # response = self.new_chat.askAI(st.session_state.userid, st.session_state.questionInput, callbacks=None)
                # st.session_state.questions.append(st.session_state.questionInput)
                # st.session_state.responses.append(response)   
        # 'Chat' object has no attribute 'question': exception occurs when user has not asked a question, in this case, pass
        except AttributeError:
            pass

    def resume_template_popup(self, resume_type):

        """ Popup window for user to select a resume template based on the resume type. """

        print("TEMPLATE POPUP")
        dir_path="./resume_templates/functional/"
        if resume_type == "functional" or resume_type=="chronological":
            dir_path = "./resume_templates/functional/"
        # modal = Modal(key="template_popup", title=f"")
        # with modal.container():
        with st.form( key='template_form', clear_on_submit=True):
            img_path= "../resume_templates/functional/functional-0.png"
            # img_path = "/streamlit_chatbot/static/functional-0.png"
            # st.image(img_path, caption="basic functional")
            # bootstrap 4 collapse example
            def display_image(img_path):
                # Define the HTML hyperlink with the image
                # html_string = f'<a href="{img_path}"><img src="{img_path}" width="200" caption="legend" id="img0"></a>'
                # html_string = f'<a href="{img_path}"><img src="{img_path}" onclick="saveClick(img0)" id="img0"></a>'
                html_string = f'<a href="http://lokeshdhakar.com/projects/lightbox2/images/image-1.jpg"><img src="http://lokeshdhakar.com/projects/lightbox2/images/thumb-1.jpg" width="200" caption="legend" id="img0"></a>'
                return html_string
    

            js_string = """ 
                <script language="javascript">
                    alert("test");
                    var descriptionTag = document.getElementById('description');
                    document.getElementById("img0").onclick = function() {
                        alert("image 0 clicked");
                        descriptionTag.innerText = 'image 0 clicked';
                    }
                </script>"""
            # html_form = f"""
            #     <form method="post" name="contactForm">
            #         {display_image(img_path)}
            #     </form>
            # """
            html_form =   f"""
                <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
                <link rel="stylesheet" href="../static/styles/lightbox.css">
                <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
                <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
                <div id="accordion">
                <div class="card">
                    <div class="card-header" id="headingOne">
                    <h5 class="mb-0">
                        <button class="btn btn-link" data-toggle="collapse" data-target="#collapseOne" aria-expanded="true" aria-controls="collapseOne">
                            basic templates
                        </button>
                    </h5>
                    </div>
                    <div id="collapseOne" class="collapse show" aria-labelledby="headingOne" data-parent="#accordion">
                    <div class="card-body">
                        {display_image(img_path)}
                    </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header" id="headingTwo">
                    <h5 class="mb-0">
                        <button class="btn btn-link collapsed" data-toggle="collapse" data-target="#collapseTwo" aria-expanded="false" aria-controls="collapseTwo">
                        Collapsible Group Item #2
                        </button>
                    </h5>
                    </div>
                    <div id="collapseTwo" class="collapse" aria-labelledby="headingTwo" data-parent="#accordion">
                    <div class="card-body">
                        Collapsible Group Item #2 content
                    </div>
                    </div>
                </div>
                </div>
                     <div id="descriptioncontainer">
                        <p id="description">Click on the portraits above to learn more about each member of the organisation. The description will appear here and replace this text.</p>
                </div>
                """

            components.html(
                html_form + js_string,
                # <script src="../static/js/lightbox-plus-jquery.js"></script>
                # <script src="../static/js/test.js">
                height=600,
                scrolling=True,
            )
           
        # self.set_clickable_icons(dir_path)
        # content = f"<a href='#' id='{id}'><img src='https://icons.iconarchive.com/icons/custom-icon-design/pretty-office-7/256/Save-icon.png'></a>"
        # clicked = click_detector(content, key="click_detector")
        # st.markdown(f"**{clicked} clicked**" if clicked != "" else "**No click**")
        # if clicked!="":
        #     # st.experimental_rerun()
        #     st.session_state["resume_template_file"] = f"{dir_path}functional-0.png"
        #     self.resume_template_callback()
        #     print("YAYAYAYAYAy")
        #TODO below radio is temporary
        # pick_me = st.radio("Radio", [1, 2, 3])
        # if pick_me:
        #     st.session_state["resume_template_file"] = f"{dir_path}functional-0.png"
                # st.experimental_rerun()
        st.form_submit_button(label='Submit', on_click=self.resume_template_callback)
        # if modal.close():
        #     st.experimental_rerun()


    def resume_template_callback(self):

        """ Calls the resume_rewriter tool to rewrite the resume according to the chosen resume template. """

        resume_template_file = st.session_state.resume_template_file
        question = f"""Please help user rewrite their resume using the resume_rewriter tool with the following resume_template_file:{resume_template_file}. """
        st.session_state.input = question
        self.question_callback()


    def set_clickable_icons(self, dir_path):

        """ Displays a set of clickable images from a directory of resume template images. """

        images = []
        for path in Path(dir_path).glob('**/*.png'):
            file = str(path)
            with open(file, "rb") as image:
                encoded = base64.b64encode(image.read()).decode()
                images.append(f"data:image/png;base64,{encoded}")
        clicked = clickable_images(
            images,
            titles=[f"Image #{str(i)}" for i in range(2)],
            div_style={"display": "flex", "justify-content": "center", "flex-wrap": "wrap"},
            img_style={"margin": "5px", "height": "200px"},
        )
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
                "aggressiveness": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4, 5],
                    "description": "describes how aggressive the statement is, the higher the number the more aggressive",
                },
                "topic": {
                    "type": "string",
                    "enum": ["personal life description", "job or program description", "company or institution description", "resume help"],
                    "description": "determines if the statement contains certain topic",
                },
            },
            "required": ["topic", "sentiment", "aggressiveness"],
        }
        response = create_tag_chain(tag_schema, user_input)
        topic = response.get("topic", "")
        # if topic == "upload files":
        #     self.file_upload_popup()
        # else: 
        if topic == "personal life description" or topic=="job or program description" or topic=="company or institution description":
            self.new_chat.update_entities(f"about me:{user_input} /n ###")
        return user_input
    
        # if check_content_safety(text_str=user_input):
        #     if evaluate_content(user_input, "a job, program, company, or institutation description or a personal background description"):
        #         self.new_chat.update_entities(f"about me:{user_input} /n ###")
        #     urls = re.findall(r'(https?://\S+)', user_input)
        #     print(urls)
        #     if urls:
        #         for url in urls:
        #             self.process_link(url)
        #     return user_input
        # else: return ""




    # def process_about_me(self, about_me: str) -> None:
    
    #     """ Processes user's about me input for content type and processes any links in the description. """

    #     content_type = """a job or study related user request. """
    #     user_request = evaluate_content(about_me, content_type)
    #     about_me_summary = get_completion(f"""Summarize the following about me, if provided, and ignore all the links: {about_me}. """)
    #     self.new_chat.update_entities(f"about me:{about_me_summary} /n ###")
    #     if user_request:
    #         self.question = about_me
    #     # process any links in the about me
    #     urls = re.findall(r'(https?://\S+)', about_me)
    #     print(urls)
    #     if urls:
    #         for url in urls:
    #             self.process_link(url)




    def process_file(self, uploaded_files: Any) -> None:

        """ Processes user uploaded files including converting all format to txt, checking content safety, and categorizing content type  """

        for uploaded_file in uploaded_files:
            file_ext = Path(uploaded_file.name).suffix
            filename = str(uuid.uuid4())+file_ext
            tmp_save_path = os.path.join(temp_path, st.session_state.userid, filename)
            with open(tmp_save_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            end_path =  os.path.join(save_path, st.session_state.userid, Path(filename).stem+'.txt')
            # Convert file to txt and save it to uploads
            convert_to_txt(tmp_save_path, end_path)
            content_safe, content_type, content_topics = check_content(end_path)
            print(content_type, content_safe, content_topics) 
            if content_safe and content_type!="empty":
                st.write("File successfully uploaded!")
                self.update_entities(content_type, content_topics, end_path)
            else:
                st.error(f"Failed processing {Path(uploaded_file.name).root}. Please try another file!")
                # st.session_state.upload_error.markdown(f"{Path(uploaded_file.name).root} failed. Please try another file!")
                os.remove(end_path)
        

    def process_link(self, link: Any) -> None:

        """ Processes user shared links including converting all format to txt, checking content safety, and categorizing content type """

        end_path = os.path.join(save_path, st.session_state.userid, str(uuid.uuid4())+".txt")
        if html_to_text([link], save_path=end_path):
        # if (retrieve_web_content(posting, save_path = end_path)):
            content_safe, content_type, content_topics = check_content(end_path)
            print(content_type, content_safe, content_topics) 
            if content_safe and content_type!="empty" and content_type!="browser error":
                self.update_entities(content_type, content_topics, end_path)
            else:
                st.error(f"Failed processing {link}. Please try another link!")
                # st.session_state.upload_error.markdown(f"{link} failed. Please try another link!")
                os.remove(end_path)


    def update_entities(self, content_type:str, content_topics:str, end_path:str) -> str:

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
            self.update_vectorstore(content_topics, end_path)


    def update_vectorstore(self, content_topics: str, end_path: str) -> None:

        """ Update vector store for chat agent. """

        entity = f"""topics: {str(content_topics)} """
        self.new_chat.update_entities(entity)
        vs_name = "user_material"
        vs = merge_faiss_vectorstore(vs_name, end_path)
        vs_path =  os.path.join(save_path, st.session_state.userid, vs_name)
        vs.save_local(vs_path)
        entity = f"""user_material_path: {vs_path} /n ###"""
        self.new_chat.update_entities(entity)





if __name__ == '__main__':

    advisor = Chat()
    # asyncio.run(advisor.initialize())
