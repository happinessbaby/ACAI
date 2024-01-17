import streamlit as st
import extra_streamlit_components as stx
from my_component import my_component
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from cookie_manager import get_cookie, set_cookie, delete_cookie, get_all_cookies
import time
import datetime
from streamlit_modal import Modal
from dynamodb_utils import save_user_info
from aws_manager import get_aws_session
from dynamodb_utils import init_table, check_attribute_exists
from streamlit_plannerbot import Planner
import streamlit.components.v1 as components
from lancedb_utils import create_table, add_to_table
from utils.langchain_utils import create_record_manager, create_vectorstore, update_index, split_doc_file_size
from utils.common_utils import get_generated_responses, check_content
from utils.basic_utils import read_txt, delete_file, convert_to_txt
from typing import Any
from pathlib import Path
import faiss
import re
import uuid

st.set_page_config(layout="wide")
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

login_file = os.environ["LOGIN_FILE"]
STORAGE = os.environ['STORAGE']
bucket_name = os.environ["BUCKET_NAME"]



class User():
    
    cookie = get_cookie("userInfo")
    aws_session = get_aws_session()
    # st.write(get_all_cookies())

    def __init__(self):
        # NOTE: userId is retrieved from browser cookie
        time.sleep(2)
        if self.cookie:
            self.userId = re.split("###|@", self.cookie)[1]
             # self.userId = self.cookie.split("###")[1]
            print(self.userId)
        else:
            self.userId = None 
        if "sessionId" not in st.session_state:
            st.session_state["sessionId"] = str(uuid.uuid4())
            print(f"Session: {st.session_state.sessionId}")
        self._init_session_states(self.userId, st.session_state.sessionId)
        self._init_user()

    @st.cache_data()
    def _init_session_states(_self, userId, sessionId):

        if STORAGE=="CLOUD":
            st.session_state["s3_client"] = _self.aws_session.client('s3') 
            st.session_state["bucket_name"] = bucket_name
            st.session_state["storage"] = "CLOUD"
            st.session_state["user_path"] = os.environ["S3_USER_PATH"]
        elif STORAGE=="LOCAL":
            st.session_state["s3_client"] = None
            st.session_state["bucket_name"] = None
            st.session_state["storage"] = "LOCAL"
            st.session_state["user_path"] = os.environ["USER_PATH"]




    def _init_user(self):

        """ Initalizes user page according to user's sign in status"""

        with open(login_file) as file:
            config = yaml.load(file, Loader=SafeLoader)
        authenticator = stauth.Authenticate( config['credentials'], config['cookie']['name'], config['cookie']['key'], config['cookie']['expiry_days'], config['preauthorized'] )
        if self.cookie is None:
            self.sign_in(authenticator)
            # try:
            #     if st.session_state["signin_modal"]:
            #          self._sign_in(authenticator)
            #     else:
            #         st.sidebar.button("signin")
            # except KeyError:
            #     st.session_state["signin_modal"]=True
            #     self._sign_in(authenticator)
        else:
            if "init_user" not in st.session_state:
                self.about_me_popup1()
            if "init_user" in st.session_state and st.session_state["init_user"]==True and "init_user2" not in st.session_state:
                self.about_me_popup2()
            logout = authenticator.logout('Logout', 'sidebar')
            if logout:
                # Hacky way to log out of Google
                with st.spinner("logging out"):
                    print(get_all_cookies())
                    delete_cookie(get_cookie("userInfo"), key="deleteCookie")
                    _ = my_component("signout", key="signout")
            with st.sidebar:
                update = st.button(label="update profile", key="update_profile", on_click=self.update_personal_info)
            # if "plannerbot" not in st.session_state:
            #     st.session_state["plannerbot"]=Planner(self.userId)
            # try:
            #     st.session_state.plannerbot._create_user_page()
            # except Exception as e:
            #     raise e
    




    def sign_in(self, authenticator:stauth.Authenticate):

        modal = Modal("   ", key="sign_in_popup", max_width=500, close_button=False)
        with modal.container():
            # st.button("X", on_click=self.close_modal, args=["signin_modal"])
            user_info = my_component(name="signin", key="signin")
            st.markdown("or")
            with st.expander(label="log in"):
                name, authentication_status, username = authenticator.login('', 'main')
                col1, col2 = st.columns(2, gap='large')
                with col2:
                    forgot_password = st.button(label="forgot my password", key="forgot", type="primary")

            print(user_info)
            if user_info!=-1:
                print(f"user signed in through google: {user_info}")
                # NOTE: Google's token expires after 1 hour
                set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
                # st.write(get_all_cookies())
                # st.rerun()
            # print(name, authentication_status, username)
            if authentication_status:
                print("user signed in through system")
                set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
            elif authentication_status == False:
                st.error('Username/password is incorrect')
            # elif authentication_status == None:
            #     st.warning('Please enter your username and password')
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
            col1, col2 = st.columns(2, gap='large')
            with col1:
                sign_up = st.button(label="sign up", key="signup", on_click=self.sign_up, args=[authenticator], type="primary")
            


    def sign_up(self, authenticator:stauth.Authenticate):

        try:
            modal = Modal("Welcome", key="register", max_width=500)
            with modal.container():
                if authenticator.register_user("Create an account", "main", preauthorization=False):
                    st.success("User registered successfully")
                    set_cookie("userInfo", user_info, key="setCookie", path="/", expire_at=datetime.datetime.now()+datetime.timedelta(hours=1))
        except Exception as e:
            st.error(e)
    

        # with open(login_file, "w") as file:
        #     yaml.dump(config, file, default_flow_style=False)



    # def close_modal(self, name):
    #     st.session_state[name]=False


    # def about_me_popup(_self) -> None:
    
    #     """ Processes user's about me input. """

    #     modal = Modal(title="", key="about_popup", max_width=800, close_button=False)
    #     if st.session_state.get("past", False) and st.session_state.get("present", False) and st.session_state.get("future", False) :
    #         st.session_state.disabled=False
    #     else:
    #         st.session_state.disabled=True
    #     with modal.container():
    #         st.button("X", on_click=_self.close_modal, args=["about_me_modal"])
    #         selected = stx.stepper_bar(steps=["Self Description", "Current Situation", "Career Goals"])
    #         if selected==0:
    #             st.text_input(
    #             label="What can I know about you?", 
    #             placeholder="Tell me about yourself", 
    #             key = "about_past", 
    #             on_change=_self.about_me_form_check
    #             )
    #         elif selected==1:
    #             st.text_input(
    #             label="What takes you here?",
    #             placeholder = "Tell me about your present situation",
    #             key="about_present",
    #             on_change = _self.about_me_form_check
    #             )
    #         elif selected==2:
    #             st.text_input(
    #             label="What can I do for you?",
    #             placeholder = "Tell me about your career goals",
    #             key="about_future",
    #             on_change=_self.about_me_form_check,
    #             )
    #         submitted = st.button("Submit", on_click=_self.form_callback2, disabled=st.session_state.disabled)
    #         if submitted:
    #             st.session_state["init_user"]=True
    #             modal.close()

    def about_me_popup1(self):


        if st.session_state.get("first_name", False) and st.session_state.get("last_name", False) and st.session_state.get("birthday", False) and st.session_state.get("grad_year", False) and st.session_state.get("degree", False) and st.session_state.get("job", False) and st.session_state.get("job_level", False):
            st.session_state.disabled1=False
        else:
            st.session_state.disabled1=True
        st.markdown("**Basic Information**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.text_input("First Name", key="first_namex", on_change=self.about_me_form_check)
        with c2:
            st.text_input("Last Name", key="last_namex", on_change=self.about_me_form_check)
        with c3:
            st.date_input("Date of Birth", datetime.date(2019, 7, 6), min_value=datetime.date(1950, 1, 1), key="birthdayx", on_change=self.about_me_form_check)
        # c1, c2, c3, c4=st.columns(4)
        # with c1:
        #     st.text("Date of Birth")
        # with c2:
        #     st.selectbox("day", key="day", options=(1, 2, 3))
        # with c3:
        #     st.selectbox("month", key="month", options=(1, 2, 3))
        # with c4: 
        #     st.selectbox("year", key="year", options=(1, 2, 3))
        c1, c2, c3, c4 = st.columns([0.5, 1, 1, 1])
        with c1:
            st.text("Highest Level of \n Education")
            # st.text_input("School", key="schoolx")
        with c2:
            st.text_input("Year of Graduation", key="grad_yearx", on_change=self.about_me_form_check)
        with c3:
            st.selectbox("Degree", options=(1, 2, 3), key="degreex", on_change=self.about_me_form_check)
        with c4:
            st.text_input("Area of study", key="studyx", placeholder="please separate each with a comma", on_change=self.about_me_form_check)
        c1, c2, c3 = st.columns([0.5, 1, 1])
        with c1:
            st.text("""Work Experience of \n Your Career of Choice""")
            # components.html( """<div style="text-align: bottom"> Work Experience</div>""")
        with c2:
            st.text_input("Job Title", key="jobx", on_change=self.about_me_form_check)
        with c3:
            st.select_slider("Level",  options=["no experience", "entry level", "junior level", "mid level", "senior level"], key='job_levelx', on_change=self.about_me_form_check)   
        st.file_uploader(label="Default Resume", key="resumex", on_change=self.about_me_form_check,)
        st.button(label="Next", on_click=self.form_callback1, disabled=st.session_state.disabled1)



    def about_me_popup2(self):

        # with st.form(key="about_me2", clear_on_submit=False):
        if st.session_state.get("past", False) and st.session_state.get("present", False) and st.session_state.get("future", False) :
            st.session_state.disabled=False
        else:
            st.session_state.disabled=True
        selected = stx.stepper_bar(steps=["Self Description", "Current Situation", "Career Goals"])
        if selected==0:
            st.text_area(
            label="What can I know about you?", 
            placeholder="Tell me about yourself", 
            key = "about_past", 
            on_change=self.about_me_form_check
            )
        elif selected==1:
            st.text_area(
            label="What takes you here?",
            placeholder = "Tell me about your present situation",
            key="about_present",
            on_change =self.about_me_form_check
            )
        elif selected==2:
            st.text_area(
            label="What can I do for you?",
            placeholder = "Tell me about your career goals",
            key="about_future",
            on_change=self.about_me_form_check,
            )
        submitted = st.button("Submit", on_click=self.form_callback2, disabled=st.session_state.disabled)
        if submitted:
            st.session_state["init_user2"]=True



    def form_callback1(self):

        # try:
        #     first_name=st.session_state.first_name
        # except AttributeError:
        #     st.write("first name is required")
        st.session_state["init_user"]=True

                
    def form_callback2(self):

        #TODO Save all the user info to LanceDB
        table=create_table(self.userId, schema="userInfo", mode="overwrite")
        basic_info_text = f""" User's name is {st.session_state.first_name} {st.session_state.last_name}. User is born in {st.session_state.birthday}. 
        User graduated in {st.session_state.grad_year}, with a degree in {st.session_state.degree}, and area of study in {st.session_state.study}.
        User's career of choice is {st.session_state.job}. The work experience level for this job is {st.session_state.job_level}
        """
        description_text = f""" user's name is {st.session_state.first_name} {st.session_state.last_name}. The following are user's self-description, current situation, and future career goals.
        self-description: {st.session_state.self_description} \
        current situation: {st.session_state.current_situation} \
        career goals: {st.session_state.career_goals} \
        """   
        text = basic_info_text + description_text
        save_path =  os.path.join(st.session_state.user_path, self.userId, "user_description.txt")
        with open(save_path, "wb") as f:
            f.write(text)
        docs = split_doc_file_size(save_path, "file", storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
        docs = self.process_file(st.session_state.resume)
        # update user information to vectorstore
        vectorstore=create_vectorstore("elasticsearch", index_name=self.userId)
        record_manager=create_record_manager(self.userId)
        update_index(docs, record_manager, vectorstore)
        # table.add([{"text":text}])
        # field_names = ["first_name", "last_name", "birthday", "grad_year", "degree", "study", "job", "job_level", "past", "present", "future"]
        # field_values=[st.session_state.first_name, st.session_state.last_name, st.session_state.birthday, st.session_state.grad_year, 
        #               st.session_state.degree, st.session_state.study, st.session_state.job, st.session_state.job_level, 
        #               st.session_state.past, st.session_state.present, st.session_state.future]
        # for field_name, field_value in zip(field_names, field_values):
        #     add_to_table(field_name, field_value, table=table)


        
    def about_me_form_check(self):

        # Hacky way to save input text for stepper bar for batch submission
        try:
            st.session_state["past"] = st.session_state.about_past
        except AttributeError:
            pass
        try:
            st.session_state["present"] = st.session_state.about_present
        except AttributeError:
            pass
        try:
            st.session_state["future"] = st.session_state.about_future
        except AttributeError:
            pass
        try:
            st.session_state["first_name"] = st.session_state.first_namex
        except AttributeError:
            pass
        try:
            st.session_state["last_name"] = st.session_state.last_namex
        except AttributeError:
            pass
        try:
            st.session_state["birthday"] = st.session_state.birthdayx
        except AttributeError:
            pass
        # try:
        #     st.session_state["school"] = st.session_state.schoolx
        # except AttributeError:
        #     pass
        try:
            st.session_state["grad_year"] = st.session_state.grad_yearx
        except AttributeError:
            pass
        try:
            st.session_state["degree"] = st.session_state.degreex
        except AttributeError:
            pass
        try:
            st.session_state["study"] = st.session_state.studyx
        except AttributeError:
            pass
        try:
            st.session_state["job"] = st.session_state.jobx
        except AttributeError:
            pass
        try:
            st.session_state["job_level"] = st.session_state.job_levelx
        except AttributeError:
            pass
        try:
            st.session_state["resume"] = st.session_state.resumex
        except AttributeError:
            pass

    def process_file(self, uploaded_files: Any) -> None:

        """ Processes user uploaded files including converting all format to txt, checking content safety, and categorizing content type  """
        # with st.session_state.file_loading, st.spinner("Processing..."):
        # with st.session_state.spinner_placeholder, st.spinner("Processing..."):
        for uploaded_file in uploaded_files:
            file_ext = Path(uploaded_file.name).suffix
            filename = str(uuid.uuid4())+file_ext
            save_path = os.path.join(st.session_state.user_path, self.userId, filename)
            end_path =  os.path.join(st.session_state.user_path, self.userId, Path(filename).stem+'.txt')
            st.session_state["resume_path"] = end_path
            if STORAGE=="LOCAL":
                with open(save_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
            elif STORAGE=="CLOUD":
                st.session_state.s3_client.put_object(Body=uploaded_file.getvalue(), Bucket=bucket_name, Key=save_path)
                print("Successful written file to S3")
            # Convert file to txt and save it 
            convert_to_txt(save_path, end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client) 
            content_safe, content_type = check_content(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
            print(content_type, content_safe) 
            if content_safe and content_type=="resume":
                st.toast(f"your {content_type} is successfully submitted")
            else:
                delete_file(end_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                delete_file(save_path, storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
                st.toast(f"Failed processing {Path(uploaded_file.name).root}. Please try another file!")
            docs = split_doc_file_size(path=end_path, file_type="file", storage=st.session_state.storage, bucket_name=st.session_state.bucket_name, s3=st.session_state.s3_client)
            return docs

  
    def update_personal_info(self):

        # update user information to vectorstore
        vectorstore=create_vectorstore("elasticsearch", index_name=self.userId)
        record_manager=create_record_manager(self.userId)
        update_index(docs, record_manager, vectorstore)








if __name__ == '__main__':
    user = User()

